import hmac
import json
import os
import re
import threading
from datetime import datetime, timezone
from functools import wraps

import markdown
from dotenv import load_dotenv
from flask import (
    Flask,
    Response,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect

import database_helper
import notifications

# --- Form input bounds (server-side; the client also has maxlength) ---
MAX_NAME_LEN = 100
MAX_EMAIL_LEN = 200
MAX_COUNTRY_LEN = 100
MAX_MESSAGE_LEN = 2000

load_dotenv()

DEBUG_MODE = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
SECRET_KEY = os.getenv('SECRET_KEY', '')
PLACEHOLDER_SECRET = 'change-me-in-production'

if not DEBUG_MODE and (not SECRET_KEY or SECRET_KEY == PLACEHOLDER_SECRET):
    raise RuntimeError(
        'SECRET_KEY must be set to a strong unique value when FLASK_DEBUG is not True. '
        "Generate one with: python -c 'import secrets; print(secrets.token_hex(32))'"
    )

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = SECRET_KEY or PLACEHOLDER_SECRET

# Session cookie hardening. SECURE only in production (HTTPS); requiring it
# in dev would lose the cookie over plain http://localhost.
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=not DEBUG_MODE,
    PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 30,  # 30 days — lang preference survives browser restart
)

csrf = CSRFProtect(app)

# Rate limiting. In-memory storage is fine for a single Flask process; for
# multi-worker deployments, point RATELIMIT_STORAGE_URI at redis.
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[],  # nothing by default — opt-in per route
    storage_uri=os.getenv('RATELIMIT_STORAGE_URI', 'memory://'),
)

# --- Translation system ---
SUPPORTED_LANGS = ['en', 'de']
DEFAULT_LANG = 'en'
_translations_cache = {}
_translations_lock = threading.Lock()


def load_translations(lang):
    # Lock-free fast path for the common case (cache hit). Dict reads are
    # atomic in CPython, so a missed-then-loaded entry is safe to read here.
    cached = _translations_cache.get(lang)
    if cached is not None:
        return cached
    with _translations_lock:
        # Re-check under the lock — another thread may have populated it
        # while we were waiting.
        cached = _translations_cache.get(lang)
        if cached is not None:
            return cached
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'translations', f'{lang}.json')
        if os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                _translations_cache[lang] = json.load(f)
        else:
            _translations_cache[lang] = {}
        return _translations_cache[lang]


@app.before_request
def set_language():
    lang = request.args.get('lang')
    if lang in SUPPORTED_LANGS:
        session['lang'] = lang
        session.permanent = True
    g.lang = session.get('lang', DEFAULT_LANG)
    g.t = load_translations(g.lang)


# Defense-in-depth security headers. CSP allows 'unsafe-inline' for the
# inline <script> bootstrap, JSON-LD, and cookie-consent script; full
# nonce/hash CSP would be stricter but the inline scripts here are stable
# and the XSS surface is small (no user-generated content rendered).
_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self' mailto:; "
    "object-src 'none'"
)


@app.after_request
def add_security_headers(resp):
    resp.headers.setdefault('Content-Security-Policy', _CSP)
    resp.headers.setdefault('X-Content-Type-Options', 'nosniff')
    resp.headers.setdefault('X-Frame-Options', 'DENY')
    resp.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
    resp.headers.setdefault('Permissions-Policy',
                            'camera=(), microphone=(), geolocation=(), interest-cohort=()')
    if not DEBUG_MODE:
        # HSTS only in prod (HTTPS). 1 year, includeSubDomains; no preload yet.
        resp.headers.setdefault('Strict-Transport-Security',
                                'max-age=31536000; includeSubDomains')
    return resp


SITE_URL = os.getenv('SITE_URL', 'https://niklasclasen.com')


@app.context_processor
def inject_translations():
    return dict(t=g.t, lang=g.lang, SUPPORTED_LANGS=SUPPORTED_LANGS, SITE_URL=SITE_URL)

# Initialize database on startup
database_helper.create_database()

# Case-study slugs — drive the /projects/<slug> route + sitemap. Kept as a
# hardcoded list now that all scenarios render from a single shared template
# (templates/projects/_case_study.html) driven by translations.
project_slugs = ['powerbi-migration', 'fabric-lakehouse', 'automated-reporting']


# --- Blog helpers ---

_BLOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'blog_posts')
_blog_cache = {'mtimes': None, 'posts': []}
_blog_cache_lock = threading.Lock()


_WORDS_PER_MINUTE = 200  # standard reading-time heuristic
_TOC_MIN_HEADINGS = 3    # don't bother rendering a TOC for short posts


def _flatten_toc(toc_tokens):
    """Walk the markdown `toc` extension's nested toc_tokens into a flat list
    of {level, name, id} dicts suitable for rendering a single-column TOC."""
    out = []
    def walk(node, depth):
        out.append({'level': node.get('level', depth), 'name': node.get('name', ''), 'id': node.get('id', '')})
        for child in node.get('children', []) or []:
            walk(child, depth + 1)
    for top in toc_tokens or []:
        walk(top, 2)
    return out


def _parse_blog_post(filepath, filename):
    with open(filepath, encoding='utf-8') as f:
        content = f.read()
    frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if not frontmatter_match:
        return None
    meta_text = frontmatter_match.group(1)
    body = content[frontmatter_match.end():]
    meta = {}
    for line in meta_text.strip().split('\n'):
        key, _, value = line.partition(':')
        meta[key.strip()] = value.strip()
    tags_raw = meta.get('tags', '')
    tags = [t.strip() for t in tags_raw.split(',') if t.strip()] if tags_raw else []

    # Render once with the toc extension so headings get id attributes and we
    # can build a sidebar TOC from md.toc_tokens.
    md = markdown.Markdown(extensions=['fenced_code', 'tables', 'toc'],
                           extension_configs={'toc': {'permalink': False}})
    content_html = md.convert(body)
    toc = _flatten_toc(getattr(md, 'toc_tokens', []))

    # Reading time: count whitespace-separated tokens in the raw body
    # (markdown source). Strip frontmatter already done. Round up.
    word_count = len(re.findall(r'\S+', body))
    reading_minutes = max(1, round(word_count / _WORDS_PER_MINUTE))

    return {
        'slug': filename.replace('.md', ''),
        'title': meta.get('title', 'Untitled'),
        'date': meta.get('date', ''),
        'summary': meta.get('summary', ''),
        'tags': tags,
        # Optional `cover:` frontmatter — path relative to /static/.
        # If set, blog_post.html uses it as og:image for nicer social shares.
        'cover': meta.get('cover', ''),
        'content_html': content_html,
        'toc': toc if len(toc) >= _TOC_MIN_HEADINGS else [],
        'reading_minutes': reading_minutes,
        'word_count': word_count,
    }


def get_blog_posts():
    """Return cached posts, re-parsing only when a markdown file's mtime changes.

    Thread-safe: cache hits take the lock-free fast path; the rebuild path is
    serialized under _blog_cache_lock so two concurrent first-callers don't
    both parse the markdown.
    """
    if not os.path.exists(_BLOG_DIR):
        return []
    files = [f for f in os.listdir(_BLOG_DIR) if f.endswith('.md')]
    mtimes = {f: os.path.getmtime(os.path.join(_BLOG_DIR, f)) for f in files}
    if mtimes == _blog_cache['mtimes']:
        return _blog_cache['posts']
    with _blog_cache_lock:
        # Re-check under the lock to avoid duplicate work when threads race.
        if mtimes == _blog_cache['mtimes']:
            return _blog_cache['posts']
        posts = []
        for filename in files:
            post = _parse_blog_post(os.path.join(_BLOG_DIR, filename), filename)
            if post is not None:
                posts.append(post)
        posts.sort(key=lambda p: p['date'], reverse=True)
        _blog_cache['mtimes'] = mtimes
        _blog_cache['posts'] = posts
        return posts


# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/projects')
def projects():
    return render_template('projects.html')


@app.route('/services')
def services():
    return render_template('services.html')


@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/process')
def process():
    return render_template('process.html')


@app.route('/calculator')
def calculator():
    return render_template('calculator.html')


@app.route('/checklist')
def checklist():
    return render_template('checklist.html')


@app.route('/privacy')
def privacy():
    return render_template('privacy.html')


@app.route('/sw.js')
def service_worker():
    return send_from_directory(app.static_folder, 'sw.js', mimetype='application/javascript')


@app.route('/manifest.json')
def manifest():
    return send_from_directory(app.static_folder, 'manifest.json', mimetype='application/manifest+json')


@app.route('/search')
def search():
    query = request.args.get('q', '').strip().lower()
    if not query:
        return redirect(url_for('index'))

    # Titles/descriptions pulled from translations so search results are
    # localized along with the rest of the site.
    titles = g.t.get('search', {}).get('page_titles', {})
    pages = [
        {'title': titles.get('home',       'Home'),       'url': '/',           'desc': titles.get('home_desc',       '')},
        {'title': titles.get('services',   'Services'),   'url': '/services',   'desc': titles.get('services_desc',   '')},
        {'title': titles.get('projects',   'Projects'),   'url': '/projects',   'desc': titles.get('projects_desc',   '')},
        {'title': titles.get('blog',       'Blog'),       'url': '/blog',       'desc': titles.get('blog_desc',       '')},
        {'title': titles.get('process',    'Process'),    'url': '/process',    'desc': titles.get('process_desc',    '')},
        {'title': titles.get('calculator', 'Calculator'), 'url': '/calculator', 'desc': titles.get('calculator_desc', '')},
        {'title': titles.get('checklist',  'Checklist'),  'url': '/checklist',  'desc': titles.get('checklist_desc',  '')},
        {'title': titles.get('contact',    'Contact'),    'url': '/contact',    'desc': titles.get('contact_desc',    '')},
    ]

    results = [p for p in pages if query in p['title'].lower() or query in p['desc'].lower()]

    # Also search blog posts
    for post in get_blog_posts():
        if query in post['title'].lower() or query in post['summary'].lower():
            results.append({'title': post['title'], 'url': f"/blog/{post['slug']}", 'desc': post['summary']})

    return render_template('search.html', query=query, results=results)


@app.route('/download-checklist', methods=['POST'])
@limiter.limit('5 per hour')
def download_checklist():
    # Honeypot: silently 404 bots that fill the hidden field.
    if request.form.get('website', '').strip():
        return render_template('404.html'), 404

    name = request.form.get('name', '').strip()[:MAX_NAME_LEN]
    email = request.form.get('email', '').strip()[:MAX_EMAIL_LEN]

    if not name or not email:
        flash('Please enter your name and email.', 'error')
        return redirect(url_for('checklist'))

    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        flash('Please enter a valid email address.', 'error')
        return redirect(url_for('checklist'))

    try:
        database_helper.insert_lead(name, email, 'checklist')
    except Exception:
        pass

    try:
        notifications.send_lead_notification(name, email, source='checklist')
    except Exception:
        pass

    return send_from_directory(
        os.path.join(app.static_folder, 'downloads'),
        'power-bi-performance-checklist.pdf',
        as_attachment=True
    )


@app.route('/projects/<slug>')
def project(slug):
    if slug in project_slugs:
        # All three case studies share one template; the slug indexes into
        # t.case_study.details for the per-scenario tech / challenge / impact.
        return render_template('projects/_case_study.html', slug=slug)
    return render_template('404.html'), 404


# Legacy URLs (with case-study- prefix and .html suffix) → 301 to clean slug.
@app.route('/projects/case-study-<slug>.html')
def project_legacy(slug):
    if slug in project_slugs:
        return redirect(url_for('project', slug=slug), code=301)
    return render_template('404.html'), 404


@app.route('/blog')
def blog():
    posts = get_blog_posts()
    all_tags = sorted(set(tag for post in posts for tag in post.get('tags', [])))
    active_tag = request.args.get('tag', '')
    if active_tag:
        filtered = [p for p in posts if active_tag in p.get('tags', [])]
    else:
        filtered = posts
    return render_template('blog.html', posts=filtered, all_tags=all_tags, active_tag=active_tag)


def _related_posts(posts, current, limit=3):
    """Pick the most relevant siblings to `current` from `posts`.

    Score = number of overlapping tags. Tiebreak: more-recent post first
    (date desc). If no posts share any tag (e.g., a single-post site), fall
    back to the most recent siblings.
    """
    current_tags = set(current.get('tags', []))
    siblings = [p for p in posts if p['slug'] != current['slug']]

    def score(p):
        overlap = len(current_tags & set(p.get('tags', [])))
        # Higher overlap wins; within a tie, more-recent date wins
        return (overlap, p.get('date', ''))

    siblings.sort(key=score, reverse=True)
    return siblings[:limit]


@app.route('/blog/<slug>')
def blog_post(slug):
    posts = get_blog_posts()
    post = next((p for p in posts if p['slug'] == slug), None)
    if post is None:
        return render_template('404.html'), 404
    related = _related_posts(posts, post)
    return render_template('blog_post.html', post=post, related=related)


@app.route('/submit_contact_form', methods=['POST'])
@limiter.limit('5 per hour')
def submit_contact_form():
    # Honeypot — a hidden field named "website" that real users don't see.
    # Bots that auto-fill every input populate it; silently drop them.
    if request.form.get('website', '').strip():
        return redirect(url_for('thank_you', name=request.form.get('firstname', '').strip()))

    firstname = request.form.get('firstname', '').strip()[:MAX_NAME_LEN]
    lastname = request.form.get('lastname', '').strip()[:MAX_NAME_LEN]
    country = request.form.get('country', '').strip()[:MAX_COUNTRY_LEN]
    email = request.form.get('email', '').strip()[:MAX_EMAIL_LEN]
    message = request.form.get('message', '').strip()[:MAX_MESSAGE_LEN]

    # Validate required fields
    if not all([firstname, lastname, email, message]):
        flash('Please fill in all required fields.', 'error')
        return redirect(url_for('contact'))

    # Basic email validation
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        flash('Please enter a valid email address.', 'error')
        return redirect(url_for('contact'))

    try:
        database_helper.insert_contact_request(firstname, lastname, country, email, message)
    except Exception:
        flash('Something went wrong. Please try again later.', 'error')
        return redirect(url_for('contact'))

    # Notify the operator (SMTP if configured, stderr fallback otherwise).
    # Never let a notification failure break the user-facing flow.
    try:
        notifications.send_contact_notification(firstname, lastname, country, email, message)
    except Exception:
        pass

    return redirect(url_for('thank_you', name=firstname))


@app.route('/thank-you')
def thank_you():
    name = request.args.get('name', '')
    return render_template('thank_you.html', name=name)


# --- Analytics ---

_VALID_PATH = re.compile(r'^/[A-Za-z0-9/_.\-]{0,200}$')


@app.route('/api/pageview', methods=['POST'])
@csrf.exempt
@limiter.limit('60 per minute')
def track_pageview():
    try:
        data = request.get_json(silent=True) or {}
        path = data.get('path', request.path)
        referrer = data.get('referrer', '')
        lang = data.get('lang', g.lang)
        # Validate path so spammers can't pollute /analytics with arbitrary strings
        if not isinstance(path, str) or not _VALID_PATH.match(path):
            return '', 204
        # Cap referrer + lang length; lang must be one of the supported codes
        if not isinstance(referrer, str):
            referrer = ''
        referrer = referrer[:500]
        if lang not in SUPPORTED_LANGS:
            lang = DEFAULT_LANG
        ua = request.headers.get('User-Agent', '')[:300]
        database_helper.insert_pageview(path, referrer, lang, ua)
    except Exception:
        pass
    return '', 204


def _require_analytics_auth(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        expected_user = os.getenv('ANALYTICS_USER', '')
        expected_pw = os.getenv('ANALYTICS_PASSWORD', '')
        if not expected_user or not expected_pw:
            return render_template('404.html'), 404
        auth = request.authorization
        if (auth and auth.username and auth.password
                and hmac.compare_digest(auth.username, expected_user)
                and hmac.compare_digest(auth.password, expected_pw)):
            return view(*args, **kwargs)
        return Response(
            'Authentication required.', 401,
            {'WWW-Authenticate': 'Basic realm="Analytics"'}
        )
    return wrapper


@app.route('/analytics')
@_require_analytics_auth
def analytics_dashboard():
    days = request.args.get('days', 30, type=int)
    stats = database_helper.get_analytics_summary(days)
    return render_template('analytics.html', stats=stats, days=days)


# --- SEO routes ---

@app.route('/sitemap.xml')
def sitemap():
    # Per-page <lastmod>. For static templates, take the file mtime.
    # For blog posts, prefer the post's frontmatter `date`; fall back to the
    # file mtime. For the home / index pages, use the most recent thing on the
    # site so Google sees activity when any content is updated.
    here = os.path.dirname(os.path.abspath(__file__))

    def template_mtime(rel_path):
        try:
            return datetime.fromtimestamp(
                os.path.getmtime(os.path.join(here, 'templates', rel_path)),
                tz=timezone.utc,
            ).date().isoformat()
        except OSError:
            return datetime.now(timezone.utc).date().isoformat()

    posts = get_blog_posts()
    # Most recent timestamp on the site (used for the home page lastmod)
    latest_post_date = max((p['date'] for p in posts), default=template_mtime('index.html'))

    pages = [
        {'url': '/',           'priority': '1.0', 'changefreq': 'weekly',  'lastmod': latest_post_date},
        {'url': '/services',   'priority': '0.9', 'changefreq': 'monthly', 'lastmod': template_mtime('services.html')},
        {'url': '/projects',   'priority': '0.8', 'changefreq': 'monthly', 'lastmod': template_mtime('projects.html')},
        {'url': '/blog',       'priority': '0.8', 'changefreq': 'weekly',  'lastmod': latest_post_date},
        {'url': '/process',    'priority': '0.7', 'changefreq': 'monthly', 'lastmod': template_mtime('process.html')},
        {'url': '/calculator', 'priority': '0.6', 'changefreq': 'monthly', 'lastmod': template_mtime('calculator.html')},
        {'url': '/checklist',  'priority': '0.6', 'changefreq': 'monthly', 'lastmod': template_mtime('checklist.html')},
        {'url': '/contact',    'priority': '0.7', 'changefreq': 'monthly', 'lastmod': template_mtime('contact.html')},
        {'url': '/privacy',    'priority': '0.3', 'changefreq': 'yearly',  'lastmod': template_mtime('privacy.html')},
    ]
    case_study_lastmod = template_mtime('projects/_case_study.html')
    for slug in project_slugs:
        pages.append({'url': f'/projects/{slug}', 'priority': '0.7', 'changefreq': 'monthly', 'lastmod': case_study_lastmod})
    for post in posts:
        pages.append({'url': f'/blog/{post["slug"]}', 'priority': '0.7', 'changefreq': 'monthly', 'lastmod': post['date']})

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
    xml += '        xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
    for page in pages:
        full_url = SITE_URL + page['url']
        xml += '  <url>\n'
        xml += f'    <loc>{full_url}</loc>\n'
        if page.get('lastmod'):
            xml += f'    <lastmod>{page["lastmod"]}</lastmod>\n'
        xml += f'    <changefreq>{page["changefreq"]}</changefreq>\n'
        xml += f'    <priority>{page["priority"]}</priority>\n'
        # hreflang alternates for each language
        for lang in SUPPORTED_LANGS:
            xml += f'    <xhtml:link rel="alternate" hreflang="{lang}" href="{full_url}?lang={lang}"/>\n'
        xml += '  </url>\n'
    xml += '</urlset>'
    return Response(xml, mimetype='application/xml')


@app.route('/robots.txt')
def robots():
    txt = f"""User-agent: *
Allow: /

Sitemap: {SITE_URL}/sitemap.xml

Disallow: /download-checklist
Disallow: /submit_contact_form
Disallow: /search
Disallow: /analytics
"""
    return Response(txt, mimetype='text/plain')


@app.route('/blog/feed.xml')
def blog_feed():
    posts = get_blog_posts()
    now = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
    xml += '<channel>\n'
    xml += '  <title>Niklas Clasen Consulting - Blog</title>\n'
    xml += f'  <link>{SITE_URL}/blog</link>\n'
    xml += '  <description>Insights on Microsoft Fabric, Power BI, and data platform strategy.</description>\n'
    xml += '  <language>en</language>\n'
    xml += f'  <lastBuildDate>{now}</lastBuildDate>\n'
    xml += f'  <atom:link href="{SITE_URL}/blog/feed.xml" rel="self" type="application/rss+xml"/>\n'
    for post in posts:
        post_url = f'{SITE_URL}/blog/{post["slug"]}'
        # Format date for RSS
        try:
            pub_date = datetime.strptime(post['date'], '%Y-%m-%d').strftime('%a, %d %b %Y 00:00:00 +0000')
        except (ValueError, KeyError):
            pub_date = now
        xml += '  <item>\n'
        xml += f'    <title>{post["title"]}</title>\n'
        xml += f'    <link>{post_url}</link>\n'
        xml += f'    <guid>{post_url}</guid>\n'
        xml += f'    <pubDate>{pub_date}</pubDate>\n'
        xml += f'    <description>{post["summary"]}</description>\n'
        xml += '  </item>\n'
    xml += '</channel>\n'
    xml += '</rss>'
    return Response(xml, mimetype='application/rss+xml')


# --- Error handlers ---

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(e):
    return render_template('500.html'), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(debug=DEBUG_MODE, port=port)
