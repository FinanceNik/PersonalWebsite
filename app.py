import os
import re
import json
import markdown
from datetime import datetime
from flask import Flask, render_template, request, flash, redirect, url_for, send_from_directory, g, session, Response, make_response
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
import database_helper

load_dotenv()

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.getenv('SECRET_KEY', 'change-me-in-production')

csrf = CSRFProtect(app)

# --- Translation system ---
SUPPORTED_LANGS = ['en', 'de']
DEFAULT_LANG = 'en'
_translations_cache = {}


def load_translations(lang):
    if lang in _translations_cache:
        return _translations_cache[lang]
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'translations', f'{lang}.json')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            _translations_cache[lang] = json.load(f)
    else:
        _translations_cache[lang] = {}
    return _translations_cache[lang]


@app.before_request
def set_language():
    lang = request.args.get('lang')
    if lang in SUPPORTED_LANGS:
        session['lang'] = lang
    g.lang = session.get('lang', DEFAULT_LANG)
    g.t = load_translations(g.lang)


SITE_URL = os.getenv('SITE_URL', 'https://niklasclasen.com')


@app.context_processor
def inject_translations():
    return dict(t=g.t, lang=g.lang, SUPPORTED_LANGS=SUPPORTED_LANGS, SITE_URL=SITE_URL)

# Initialize database on startup
database_helper.create_database()

# Build project files list at module level with correct path
_projects_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates', 'projects')
project_files = [f for f in os.listdir(_projects_dir) if f.endswith('.html')] if os.path.isdir(_projects_dir) else []


# --- Blog helpers ---

def get_blog_posts():
    posts = []
    blog_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'blog_posts')
    if not os.path.exists(blog_dir):
        return posts
    for filename in os.listdir(blog_dir):
        if not filename.endswith('.md'):
            continue
        filepath = os.path.join(blog_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if not frontmatter_match:
            continue
        meta_text = frontmatter_match.group(1)
        body = content[frontmatter_match.end():]
        meta = {}
        for line in meta_text.strip().split('\n'):
            key, _, value = line.partition(':')
            meta[key.strip()] = value.strip()
        tags_raw = meta.get('tags', '')
        tags = [t.strip() for t in tags_raw.split(',') if t.strip()] if tags_raw else []
        posts.append({
            'slug': filename.replace('.md', ''),
            'title': meta.get('title', 'Untitled'),
            'date': meta.get('date', ''),
            'summary': meta.get('summary', ''),
            'tags': tags,
            'content_html': markdown.markdown(body, extensions=['fenced_code', 'tables'])
        })
    posts.sort(key=lambda p: p['date'], reverse=True)
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

    # Simple search across page titles and blog posts
    pages = [
        {'title': 'Home', 'url': '/', 'desc': 'Homepage with expertise, technologies, certifications'},
        {'title': 'Services', 'url': '/services', 'desc': 'Power BI, Fabric, training, support packages'},
        {'title': 'Case Studies', 'url': '/projects', 'desc': 'Power BI migration, Fabric lakehouse, automated reporting'},
        {'title': 'Blog', 'url': '/blog', 'desc': 'Insights on Fabric, Power BI, and data strategy'},
        {'title': 'How I Work', 'url': '/process', 'desc': 'My 6-step consulting process'},
        {'title': 'Pricing Calculator', 'url': '/calculator', 'desc': 'Get a ballpark estimate for your project'},
        {'title': 'Free Checklist', 'url': '/checklist', 'desc': 'Power BI Performance Checklist PDF download'},
        {'title': 'Contact', 'url': '/contact', 'desc': 'Get in touch for a free consultation'},
    ]

    results = [p for p in pages if query in p['title'].lower() or query in p['desc'].lower()]

    # Also search blog posts
    for post in get_blog_posts():
        if query in post['title'].lower() or query in post['summary'].lower():
            results.append({'title': post['title'], 'url': f"/blog/{post['slug']}", 'desc': post['summary']})

    return render_template('search.html', query=query, results=results)


@app.route('/download-checklist', methods=['POST'])
def download_checklist():
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()

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

    return send_from_directory(
        os.path.join(app.static_folder, 'downloads'),
        'power-bi-performance-checklist.pdf',
        as_attachment=True
    )


@app.route('/projects/<filename>')
def project(filename):
    if filename in project_files:
        return render_template(f'projects/{filename}')
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


@app.route('/blog/<slug>')
def blog_post(slug):
    posts = get_blog_posts()
    post = next((p for p in posts if p['slug'] == slug), None)
    if post is None:
        return render_template('404.html'), 404
    related = [p for p in posts if p['slug'] != slug][:3]
    return render_template('blog_post.html', post=post, related=related)


@app.route('/submit_contact_form', methods=['POST'])
def submit_contact_form():
    firstname = request.form.get('firstname', '').strip()
    lastname = request.form.get('lastname', '').strip()
    country = request.form.get('country', '').strip()
    email = request.form.get('email', '').strip()
    message = request.form.get('message', '').strip()

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

    return redirect(url_for('thank_you', name=firstname))


@app.route('/thank-you')
def thank_you():
    name = request.args.get('name', '')
    return render_template('thank_you.html', name=name)


# --- Analytics ---

@app.route('/api/pageview', methods=['POST'])
@csrf.exempt
def track_pageview():
    try:
        data = request.get_json(silent=True) or {}
        path = data.get('path', request.path)
        referrer = data.get('referrer', '')
        lang = data.get('lang', g.lang)
        ua = request.headers.get('User-Agent', '')[:300]
        database_helper.insert_pageview(path, referrer, lang, ua)
    except Exception:
        pass
    return '', 204


@app.route('/analytics')
def analytics_dashboard():
    days = request.args.get('days', 30, type=int)
    stats = database_helper.get_analytics_summary(days)
    return render_template('analytics.html', stats=stats, days=days)


# --- SEO routes ---

@app.route('/sitemap.xml')
def sitemap():
    pages = [
        {'url': '/', 'priority': '1.0', 'changefreq': 'weekly'},
        {'url': '/services', 'priority': '0.9', 'changefreq': 'monthly'},
        {'url': '/projects', 'priority': '0.8', 'changefreq': 'monthly'},
        {'url': '/blog', 'priority': '0.8', 'changefreq': 'weekly'},
        {'url': '/process', 'priority': '0.7', 'changefreq': 'monthly'},
        {'url': '/calculator', 'priority': '0.6', 'changefreq': 'monthly'},
        {'url': '/checklist', 'priority': '0.6', 'changefreq': 'monthly'},
        {'url': '/contact', 'priority': '0.7', 'changefreq': 'monthly'},
        {'url': '/privacy', 'priority': '0.3', 'changefreq': 'yearly'},
    ]
    # Add case study pages
    for f in project_files:
        pages.append({'url': f'/projects/{f}', 'priority': '0.7', 'changefreq': 'monthly'})
    # Add blog posts
    for post in get_blog_posts():
        pages.append({'url': f'/blog/{post["slug"]}', 'priority': '0.7', 'changefreq': 'monthly'})

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
    xml += '        xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
    for page in pages:
        full_url = SITE_URL + page['url']
        xml += '  <url>\n'
        xml += f'    <loc>{full_url}</loc>\n'
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
"""
    return Response(txt, mimetype='text/plain')


@app.route('/blog/feed.xml')
def blog_feed():
    posts = get_blog_posts()
    now = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')

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
    return render_template('404.html'), 500


if __name__ == '__main__':
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    port = int(os.getenv('PORT', 5000))
    app.run(debug=debug, port=port)
