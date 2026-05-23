"""Smoke tests: every public route returns the expected status.

If one of these regresses, the user sees a broken page in production. Most
assertions are just status codes; a few sanity-check body content.
"""
import base64

import pytest

PUBLIC_PAGES = [
    '/',
    '/services',
    '/projects',
    '/process',
    '/blog',
    '/calculator',
    '/checklist',
    '/contact',
    '/privacy',
    '/thank-you',
]

CASE_STUDIES = [
    '/projects/powerbi-migration',
    '/projects/fabric-lakehouse',
    '/projects/automated-reporting',
]


@pytest.mark.parametrize('path', PUBLIC_PAGES + CASE_STUDIES)
def test_public_pages_return_200(client, path):
    resp = client.get(path)
    assert resp.status_code == 200, f'{path} returned {resp.status_code}'
    assert b'<!DOCTYPE html>' in resp.data, f'{path} did not return an HTML doc'


@pytest.mark.parametrize('legacy,new', [
    ('/projects/case-study-powerbi-migration.html', '/projects/powerbi-migration'),
    ('/projects/case-study-fabric-lakehouse.html',  '/projects/fabric-lakehouse'),
    ('/projects/case-study-automated-reporting.html', '/projects/automated-reporting'),
])
def test_legacy_case_study_urls_301(client, legacy, new):
    resp = client.get(legacy, follow_redirects=False)
    assert resp.status_code == 301, f'{legacy} returned {resp.status_code}, expected 301'
    assert resp.headers['Location'].endswith(new), (
        f'{legacy} redirected to {resp.headers["Location"]}, expected to end with {new}'
    )


def test_unknown_case_study_404s(client):
    assert client.get('/projects/does-not-exist').status_code == 404
    assert client.get('/projects/case-study-does-not-exist.html').status_code == 404


def test_blog_post_renders(client):
    # Pick the first post from the cache so we don't hard-code a slug
    import app as flask_app_module
    posts = flask_app_module.get_blog_posts()
    assert posts, 'expected at least one blog post in blog_posts/'
    resp = client.get(f'/blog/{posts[0]["slug"]}')
    assert resp.status_code == 200
    assert posts[0]['title'].encode() in resp.data


def test_blog_post_404(client):
    assert client.get('/blog/nope-not-a-real-post').status_code == 404


def test_sitemap_is_xml(client):
    resp = client.get('/sitemap.xml')
    assert resp.status_code == 200
    assert resp.mimetype == 'application/xml'
    assert b'<urlset' in resp.data
    # Sitemap should include the new clean case-study URLs, not the legacy ones
    assert b'/projects/powerbi-migration<' in resp.data
    assert b'case-study-' not in resp.data


def test_sitemap_has_lastmod(client):
    """Google heavily down-weights sitemaps without <lastmod>."""
    resp = client.get('/sitemap.xml')
    body = resp.data.decode()
    assert '<lastmod>' in body, 'sitemap missing <lastmod>'
    # Spot-check: every <loc> should be followed (within ~200 chars) by a <lastmod>
    import re
    matches = re.findall(r'<loc>.*?</loc>\s*<lastmod>(\d{4}-\d{2}-\d{2})</lastmod>', body)
    assert len(matches) >= 9, (
        f'expected at least 9 URLs with lastmod, got {len(matches)}'
    )


def test_robots_txt(client):
    resp = client.get('/robots.txt')
    assert resp.status_code == 200
    assert b'Sitemap:' in resp.data
    assert b'Disallow: /analytics' in resp.data


def test_rss_feed(client):
    resp = client.get('/blog/feed.xml')
    assert resp.status_code == 200
    assert resp.mimetype == 'application/rss+xml'
    assert b'<rss' in resp.data


def test_manifest_json(client):
    resp = client.get('/manifest.json')
    assert resp.status_code == 200
    import json
    data = json.loads(resp.data)
    assert data['name'] == 'Niklas Clasen Consulting'
    assert len(data['icons']) >= 2


def test_service_worker_served_as_js(client):
    resp = client.get('/sw.js')
    assert resp.status_code == 200
    assert 'javascript' in resp.mimetype


def test_404_uses_template(client):
    resp = client.get('/this/route/does/not/exist')
    assert resp.status_code == 404
    assert b'404' in resp.data


def _render_error_template(app, name):
    """Render an error template with the same context the before_request hook
    would normally populate. Used to verify 404.html / 500.html directly."""
    from flask import g, render_template

    import app as flask_app_module
    with app.test_request_context():
        g.lang = 'en'
        g.t = flask_app_module.load_translations('en')
        return render_template(name)


def test_500_template_distinct_from_404(app):
    """500.html should exist as its own template (not aliased to 404)."""
    html = _render_error_template(app, '500.html')
    assert '500' in html
    assert 'Something Went Wrong' in html
    # Make sure we didn't accidentally fall back to the 404 copy
    assert 'Page Not Found' not in html


def test_500_handler_returns_500_status(app):
    """The internal_error handler should render 500.html with a 500 status."""
    from flask import g

    import app as flask_app_module
    with app.test_request_context():
        g.lang = 'en'
        g.t = flask_app_module.load_translations('en')
        body, status = flask_app_module.internal_error(RuntimeError('synthetic'))
    assert status == 500
    assert 'Something Went Wrong' in body
    assert '500' in body


def test_analytics_requires_auth(client):
    assert client.get('/analytics').status_code == 401


def test_analytics_rejects_wrong_password(client):
    creds = base64.b64encode(b'tester:wrong').decode()
    resp = client.get('/analytics', headers={'Authorization': f'Basic {creds}'})
    assert resp.status_code == 401


def test_analytics_accepts_right_creds(client):
    creds = base64.b64encode(b'tester:tester-pass').decode()
    resp = client.get('/analytics', headers={'Authorization': f'Basic {creds}'})
    assert resp.status_code == 200


def test_analytics_returns_404_when_creds_unset(client, monkeypatch):
    monkeypatch.setenv('ANALYTICS_USER', '')
    monkeypatch.setenv('ANALYTICS_PASSWORD', '')
    assert client.get('/analytics').status_code == 404


def test_contact_post_validates_required_fields(client):
    resp = client.post('/submit_contact_form', data={
        'firstname': '', 'lastname': '', 'email': '', 'message': ''
    }, follow_redirects=False)
    # Should redirect back to /contact with a flash, not crash
    assert resp.status_code == 302
    assert resp.headers['Location'].endswith('/contact')


def test_contact_post_rejects_bad_email(client):
    resp = client.post('/submit_contact_form', data={
        'firstname': 'Test', 'lastname': 'User',
        'email': 'not-an-email', 'message': 'hi'
    }, follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers['Location'].endswith('/contact')


def test_contact_post_success_redirects_to_thank_you(client):
    resp = client.post('/submit_contact_form', data={
        'firstname': 'Test', 'lastname': 'User', 'country': 'CH',
        'email': 'test@example.com', 'message': 'hello'
    }, follow_redirects=False)
    assert resp.status_code == 302
    assert '/thank-you' in resp.headers['Location']


def test_checklist_post_validates_email(client):
    resp = client.post('/download-checklist', data={
        'name': 'Test', 'email': 'bad'
    }, follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers['Location'].endswith('/checklist')


def test_search_redirects_when_empty(client):
    resp = client.get('/search?q=', follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers['Location'] == '/'


def test_search_returns_results(client):
    resp = client.get('/search?q=Power+BI')
    assert resp.status_code == 200
    assert b'Search Results' in resp.data


def test_pageview_endpoint_accepts_post(client):
    resp = client.post('/api/pageview', json={'path': '/test', 'lang': 'en'})
    assert resp.status_code == 204


def test_language_switch_persists_in_session(client):
    # Hitting /?lang=de should set the session lang; subsequent request without
    # the param should still render in German.
    client.get('/?lang=de')
    resp = client.get('/services')
    assert b'Dienstleistungen' in resp.data or resp.status_code == 200


def test_blog_cache_hit(client):
    """get_blog_posts should reuse the cache across calls."""
    import app as flask_app_module
    first = flask_app_module.get_blog_posts()
    cached_id = id(first)
    second = flask_app_module.get_blog_posts()
    assert id(second) == cached_id, 'second call should return the same cached list'


# --- Security headers --------------------------------------------------------

@pytest.mark.parametrize('header,expected_substr', [
    ('Content-Security-Policy', "default-src 'self'"),
    ('X-Content-Type-Options', 'nosniff'),
    ('X-Frame-Options', 'DENY'),
    ('Referrer-Policy', 'strict-origin'),
    ('Permissions-Policy', 'geolocation=()'),
])
def test_security_headers_present(client, header, expected_substr):
    resp = client.get('/')
    assert header in resp.headers, f'missing {header}'
    assert expected_substr in resp.headers[header], (
        f'{header} = {resp.headers[header]!r}, expected to contain {expected_substr!r}'
    )


def test_csp_blocks_framing(client):
    resp = client.get('/')
    assert "frame-ancestors 'none'" in resp.headers.get('Content-Security-Policy', '')


def test_session_cookie_flags_in_prod_only(app):
    """SECURE only flips on when FLASK_DEBUG != True."""
    assert app.config['SESSION_COOKIE_HTTPONLY'] is True
    assert app.config['SESSION_COOKIE_SAMESITE'] == 'Lax'
    # In the test harness FLASK_DEBUG is True, so SECURE should be False
    assert app.config['SESSION_COOKIE_SECURE'] is False


# --- Honeypot + input bounds -------------------------------------------------

def test_contact_honeypot_silently_drops_bot(client):
    """If the hidden `website` field is populated, treat as a bot.
    Should redirect like success (no flash error) but NOT persist the submission."""
    import app as flask_app_module
    before = _row_count(flask_app_module, 'contactRequests')
    resp = client.post('/submit_contact_form', data={
        'firstname': 'Bot', 'lastname': 'Spam', 'email': 'bot@spam.example',
        'message': 'hi', 'website': 'http://spam.example',
    }, follow_redirects=False)
    assert resp.status_code == 302
    after = _row_count(flask_app_module, 'contactRequests')
    assert after == before, 'honeypot trip should NOT insert into contactRequests'


def test_checklist_honeypot_returns_404(client):
    resp = client.post('/download-checklist', data={
        'name': 'Bot', 'email': 'bot@spam.example', 'website': 'spam',
    })
    assert resp.status_code == 404


def test_contact_long_message_truncated_not_rejected(client):
    """Server-side max-length: massive input is truncated, not crashed."""
    huge = 'a' * 100_000
    resp = client.post('/submit_contact_form', data={
        'firstname': 'Test', 'lastname': 'User',
        'email': 'test@example.com', 'message': huge,
    }, follow_redirects=False)
    assert resp.status_code == 302
    assert '/thank-you' in resp.headers['Location']


# --- /api/pageview validation ------------------------------------------------

def test_pageview_rejects_bogus_path(client):
    """Spammer can't fill the analytics dashboard with arbitrary strings."""
    import app as flask_app_module
    before = _row_count(flask_app_module, 'pageviews')
    resp = client.post('/api/pageview', json={
        'path': 'https://evil.example/<script>alert(1)</script>',
        'referrer': 'x' * 1000,
        'lang': 'xx',
    })
    assert resp.status_code == 204
    after = _row_count(flask_app_module, 'pageviews')
    assert after == before, 'invalid path should not insert a row'


def test_pageview_accepts_valid_path(client):
    import app as flask_app_module
    before = _row_count(flask_app_module, 'pageviews')
    resp = client.post('/api/pageview', json={'path': '/services', 'lang': 'en'})
    assert resp.status_code == 204
    assert _row_count(flask_app_module, 'pageviews') == before + 1


# --- Rate limiting -----------------------------------------------------------

def test_contact_form_rate_limit(app, client):
    """5 per hour on /submit_contact_form. 6th should 429."""
    app_module_limiter = _enable_limiter(app)
    try:
        data = {'firstname': 'T', 'lastname': 'U', 'email': 't@example.com', 'message': 'hi'}
        for _ in range(5):
            r = client.post('/submit_contact_form', data=data)
            assert r.status_code in (302, 200), f'unexpected {r.status_code} within limit'
        r = client.post('/submit_contact_form', data=data)
        assert r.status_code == 429, f'6th submit should be rate-limited, got {r.status_code}'
    finally:
        app_module_limiter.enabled = False
        app_module_limiter.reset()


# --- Helpers -----------------------------------------------------------------

def _row_count(flask_app_module, table):
    import sqlite3
    db_path = flask_app_module.database_helper.DB_PATH
    with sqlite3.connect(db_path) as conn:
        return conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]


def _enable_limiter(app):
    import app as flask_app_module
    flask_app_module.limiter.enabled = True
    flask_app_module.limiter.reset()
    return flask_app_module.limiter


# --- Notifications -----------------------------------------------------------

def test_contact_notification_logs_when_smtp_not_configured(client, monkeypatch, capsys):
    """With SMTP env vars unset, the notification falls back to stderr."""
    for var in ('SMTP_HOST', 'SMTP_USER', 'SMTP_PASSWORD', 'NOTIFY_EMAIL'):
        monkeypatch.delenv(var, raising=False)
    resp = client.post('/submit_contact_form', data={
        'firstname': 'Niklas', 'lastname': 'Tester',
        'email': 'lead@example.com', 'message': 'Real lead.',
    }, follow_redirects=False)
    assert resp.status_code == 302
    captured = capsys.readouterr()
    assert 'LEAD NOTIFICATION' in captured.err
    assert 'lead@example.com' in captured.err
    assert 'Real lead.' in captured.err


def test_notifications_module_does_not_raise_on_smtp_failure(monkeypatch):
    """Even with bogus SMTP config, the notify call must not raise."""
    import notifications
    monkeypatch.setenv('SMTP_HOST', 'nonexistent.invalid')
    monkeypatch.setenv('SMTP_USER', 'u')
    monkeypatch.setenv('SMTP_PASSWORD', 'p')
    monkeypatch.setenv('NOTIFY_EMAIL', 'n@example.com')
    # Should not raise — failure logs and continues.
    notifications.send_contact_notification('A', 'B', 'CH', 'a@b.com', 'msg')


# --- Database hardening (indexes, retention, UTC timestamps) ----------------

def test_pageviews_index_exists(client):
    """idx_pageviews_ts is required for analytics queries not to full-scan."""
    import sqlite3

    import database_helper
    with sqlite3.connect(database_helper.DB_PATH) as conn:
        names = {row[1] for row in conn.execute(
            "SELECT * FROM sqlite_master WHERE type='index' AND tbl_name='pageviews'"
        ).fetchall()}
    assert 'idx_pageviews_ts' in names
    assert 'idx_pageviews_path' in names


def test_query_uses_index(client):
    """EXPLAIN QUERY PLAN should mention the index, not 'SCAN'."""
    import sqlite3

    import database_helper
    # Insert a pageview so the table isn't empty (and the planner has stats)
    database_helper.insert_pageview('/x', '', 'en', 'ua')
    with sqlite3.connect(database_helper.DB_PATH) as conn:
        plan = conn.execute(
            "EXPLAIN QUERY PLAN SELECT COUNT(*) FROM pageviews WHERE timestamp > '2026-01-01'"
        ).fetchall()
    plan_text = ' '.join(str(r) for r in plan).lower()
    assert 'idx_pageviews_ts' in plan_text or 'using index' in plan_text, (
        f'expected query to use idx_pageviews_ts; plan: {plan}'
    )


def test_inserted_timestamps_are_utc(client):
    """New rows should be in UTC, not server-local."""
    import datetime
    import sqlite3

    import database_helper
    database_helper.insert_pageview('/utc-check', '', 'en', 'ua')
    with sqlite3.connect(database_helper.DB_PATH) as conn:
        ts = conn.execute(
            "SELECT timestamp FROM pageviews WHERE path='/utc-check' ORDER BY id DESC LIMIT 1"
        ).fetchone()[0]
    # Stored format: naive ISO, no tz suffix. But the *value* is UTC.
    assert '+' not in ts and 'Z' not in ts, f'timestamp should be naive ISO, got {ts!r}'
    # Parse back and compare with now-UTC; should be within a few seconds.
    parsed = datetime.datetime.fromisoformat(ts)
    now_utc = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    delta = abs((now_utc - parsed).total_seconds())
    assert delta < 5, f'inserted timestamp drifted {delta}s from UTC now'


def test_prune_old_pageviews(client):
    """prune_old_pageviews should drop rows older than `days`."""
    import datetime
    import sqlite3

    import database_helper
    # Insert one fresh row (kept) and one fake-old row (pruned)
    database_helper.insert_pageview('/kept', '', 'en', 'ua')
    old_ts = (datetime.datetime.now(datetime.timezone.utc)
              - datetime.timedelta(days=120)).replace(tzinfo=None).isoformat()
    with sqlite3.connect(database_helper.DB_PATH) as conn:
        conn.execute(
            'INSERT INTO pageviews (timestamp, path, referrer, lang, user_agent) '
            "VALUES (?, '/old', '', 'en', 'ua')", (old_ts,)
        )
        conn.commit()

    deleted = database_helper.prune_old_pageviews(days=90)
    assert deleted >= 1

    with sqlite3.connect(database_helper.DB_PATH) as conn:
        paths = {r[0] for r in conn.execute('SELECT path FROM pageviews').fetchall()}
    assert '/old' not in paths
    assert '/kept' in paths


def test_analytics_summary_uses_naive_utc_format(client):
    """get_analytics_summary should query against the naive-UTC format and
    return zero counts (not raise) when there are no recent rows."""
    import database_helper
    # huge `days` to make sure 0 is returned even on a populated db
    stats = database_helper.get_analytics_summary(days=99999)
    assert 'total' in stats
    assert isinstance(stats['total'], int)


# --- Thread-safe cache ------------------------------------------------------

def test_blog_cache_concurrent_reads_do_not_crash():
    """Hammer get_blog_posts() from several threads; no exceptions, all return
    the same cached object once warm."""
    import threading

    import app as flask_app_module
    flask_app_module._blog_cache['mtimes'] = None  # cold start
    results = []
    errors = []
    def worker():
        try:
            results.append(id(flask_app_module.get_blog_posts()))
        except Exception as e:
            errors.append(e)
    threads = [threading.Thread(target=worker) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, f'unexpected exceptions: {errors}'
    # After warming, all threads should see the same list object
    assert len(set(results)) == 1, f'expected one cached id, got {set(results)}'


def test_translations_cache_concurrent_reads():
    """Same for load_translations — multiple threads asking for the same lang
    should converge on one cached dict without races."""
    import threading

    import app as flask_app_module
    flask_app_module._translations_cache.clear()
    results = []
    errors = []
    def worker(lang):
        try:
            results.append(id(flask_app_module.load_translations(lang)))
        except Exception as e:
            errors.append(e)
    threads = [threading.Thread(target=worker, args=('en',)) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    assert len(set(results)) == 1


# --- i18n: German render coverage --------------------------------------------

@pytest.mark.parametrize('path,german_phrase', [
    ('/',          'Meine Expertise'),
    ('/services',  'Dienstleistungen'),
    ('/projects',  'Projektszenarien'),
    ('/process',   'Mein Arbeitsprozess'),
    ('/blog',      'Einblicke'),
    ('/calculator','Projekt-Schätzer'),
    ('/checklist', 'Performance Checkliste'),
    ('/contact',   'Sprechen wir'),
    ('/privacy',   'Datenschutzerklärung'),
    ('/thank-you', 'Vielen Dank'),
    ('/projects/powerbi-migration', 'Eingesetzte Technologien'),
    ('/projects/fabric-lakehouse',  'Beispielszenario'),
    ('/projects/automated-reporting','Typische Wirkung'),
])
def test_pages_render_in_german(client, path, german_phrase):
    """When ?lang=de is set, the German strings should appear in the response."""
    resp = client.get(f'{path}?lang=de')
    assert resp.status_code == 200, f'{path}?lang=de returned {resp.status_code}'
    body = resp.data.decode('utf-8')
    assert german_phrase in body, (
        f'expected "{german_phrase}" on {path}?lang=de; first 500 chars:\n{body[:500]}'
    )


def test_de_404_uses_translated_strings(client):
    resp = client.get('/nope?lang=de')
    assert resp.status_code == 404
    assert 'Seite nicht gefunden' in resp.data.decode('utf-8')


def test_de_500_template_has_translated_copy(app):
    """500 template should resolve t.error_500.title to the German string."""
    from flask import g

    import app as flask_app_module
    with app.test_request_context():
        g.lang = 'de'
        g.t = flask_app_module.load_translations('de')
        from flask import render_template
        html = render_template('500.html')
    assert 'Etwas ist schief gelaufen' in html
    assert 'Something Went Wrong' not in html


# --- SEO + perf: fonts, OG image, theme flash --------------------------------

def test_fonts_loaded_non_blocking(client):
    """Google Fonts should load via preload + media-print swap, not via a
    render-blocking @import in CSS or a plain stylesheet link."""
    html = client.get('/').data.decode()
    # Render-blocking entry points we explicitly removed:
    assert "@import url('https://fonts.googleapis.com" not in html, \
        'Google Fonts still loaded via @import in CSS'
    # The non-blocking pattern we want:
    assert 'rel="preload" as="style"' in html
    assert 'media="print"' in html
    assert "this.media='all'" in html
    # And a <noscript> fallback so users with JS off still get the fonts:
    assert '<noscript>' in html


def test_blog_post_og_image_uses_cover_when_set(client, tmp_path, monkeypatch):
    """If a blog post has a `cover:` frontmatter field, og:image should
    point at that asset. Otherwise the site-wide og-image.png is used."""
    import app as flask_app_module
    # Drop a temp post with a cover field
    blog_dir = tmp_path / 'blog'
    blog_dir.mkdir()
    (blog_dir / 'cover-test.md').write_text(
        '---\n'
        'title: Cover Test\n'
        'date: 2026-05-23\n'
        'summary: Verify per-post OG image\n'
        'cover: image_assets/icon-512.png\n'
        '---\n\n'
        'Body.\n',
        encoding='utf-8',
    )
    monkeypatch.setattr(flask_app_module, '_BLOG_DIR', str(blog_dir))
    flask_app_module._blog_cache['mtimes'] = None  # invalidate

    resp = client.get('/blog/cover-test')
    assert resp.status_code == 200
    body = resp.data.decode()
    assert 'image_assets/icon-512.png' in body, 'cover frontmatter ignored'
    # Falls back: pick a post without cover
    flask_app_module._blog_cache['mtimes'] = None  # reset


def test_theme_bootstrap_reads_localstorage_inline(client):
    """The same <head> script that adds .js must also read the persisted theme
    so light-mode users don't see a single-frame dark flash."""
    html = client.get('/').data.decode()
    # Find the inline script in <head>
    head = html.split('</head>')[0]
    assert "localStorage.getItem('theme')" in head, \
        'theme bootstrap missing from <head>'
    assert "setAttribute('data-theme'" in head


def test_no_at_import_for_fonts_in_css(client):
    """The Google Fonts @import must not be present in base.css."""
    resp = client.get('/static/css_components/base.css')
    assert resp.status_code == 200
    assert b'fonts.googleapis.com' not in resp.data


# --- Edge cases the audit flagged --------------------------------------------

def test_invalid_lang_param_falls_back_to_default(client):
    """`?lang=xx` (or anything not in SUPPORTED_LANGS) should silently fall
    back to English rather than 500 or render with `None`."""
    resp = client.get('/?lang=fr')
    assert resp.status_code == 200
    # English copy still present:
    assert b'My Expertise' in resp.data
    # German hasn't accidentally been applied:
    assert b'Meine Expertise' not in resp.data


def test_blog_post_missing_date_does_not_crash_sitemap(client, tmp_path, monkeypatch):
    """A blog post without a `date:` frontmatter field should not crash the
    sitemap (the sitemap emits whatever's in post['date'], so empty string
    is fine; but the `max()` for latest_post_date in the sitemap route uses
    `default=` so even an empty post list is safe)."""
    import app as flask_app_module
    blog_dir = tmp_path / 'blog'
    blog_dir.mkdir()
    (blog_dir / 'no-date.md').write_text(
        '---\ntitle: Dateless\nsummary: No date in frontmatter\n---\n\nBody.\n',
        encoding='utf-8',
    )
    monkeypatch.setattr(flask_app_module, '_BLOG_DIR', str(blog_dir))
    flask_app_module._blog_cache['mtimes'] = None

    resp = client.get('/sitemap.xml')
    assert resp.status_code == 200
    assert b'<urlset' in resp.data
    # The dateless post should still show up
    assert b'/blog/no-date' in resp.data


def test_blog_post_missing_date_renders(client, tmp_path, monkeypatch):
    """The blog post route shouldn't crash on a post with no frontmatter date."""
    import app as flask_app_module
    blog_dir = tmp_path / 'blog'
    blog_dir.mkdir()
    (blog_dir / 'no-date.md').write_text(
        '---\ntitle: Dateless\nsummary: Just checking\n---\n\nBody.\n',
        encoding='utf-8',
    )
    monkeypatch.setattr(flask_app_module, '_BLOG_DIR', str(blog_dir))
    flask_app_module._blog_cache['mtimes'] = None

    resp = client.get('/blog/no-date')
    assert resp.status_code == 200
    assert b'Dateless' in resp.data


# --- Blog reading experience (reading time, TOC, share, related) -------------

def test_blog_post_reports_reading_time(client):
    """Every blog post should show its reading time."""
    import app as flask_app_module
    posts = flask_app_module.get_blog_posts()
    assert posts
    for p in posts:
        assert p['reading_minutes'] >= 1, f'{p["slug"]} reading_minutes={p["reading_minutes"]}'
        assert p['word_count'] > 0
    # And the rendered template surfaces it
    resp = client.get(f'/blog/{posts[0]["slug"]}')
    assert resp.status_code == 200
    assert b'min read' in resp.data


def test_blog_post_has_toc_when_long_enough(client):
    """Posts with 3+ headings get a TOC; short posts don't."""
    import app as flask_app_module
    posts = flask_app_module.get_blog_posts()
    assert posts
    # Each fixture post has multiple h2s — they should get a TOC
    long_post = next(p for p in posts if len(p['toc']) >= 3)
    resp = client.get(f'/blog/{long_post["slug"]}')
    body = resp.data.decode()
    assert 'blog-toc' in body
    assert 'On this page' in body
    # Every TOC entry should link to an anchor that exists in the rendered HTML
    for entry in long_post['toc']:
        assert f'id="{entry["id"]}"' in long_post['content_html'], (
            f'heading {entry["name"]!r} missing id attribute'
        )


def test_blog_post_share_buttons_present(client):
    import app as flask_app_module
    posts = flask_app_module.get_blog_posts()
    resp = client.get(f'/blog/{posts[0]["slug"]}')
    body = resp.data.decode()
    assert 'linkedin.com/sharing/share-offsite' in body
    assert 'twitter.com/intent/tweet' in body
    assert 'blog-share-copy' in body


def test_related_posts_prefer_tag_overlap():
    """_related_posts should rank by tag overlap before date."""
    import app as flask_app_module
    posts = [
        {'slug': 'a', 'date': '2026-01-01', 'tags': ['Power BI', 'DAX']},
        {'slug': 'b', 'date': '2026-02-01', 'tags': ['Fabric']},
        {'slug': 'c', 'date': '2026-03-01', 'tags': ['Power BI']},  # 1 tag overlap, newest
        {'slug': 'd', 'date': '2026-04-01', 'tags': []},            # 0 overlap, newest
    ]
    related = flask_app_module._related_posts(posts, posts[0], limit=3)
    # 'c' shares Power BI; should rank above 'd' (no overlap) and 'b' (no overlap)
    assert related[0]['slug'] == 'c'
    # Among the no-overlap posts, the more recent date wins
    assert [p['slug'] for p in related[1:]] == ['d', 'b']


def test_related_posts_falls_back_when_no_overlap():
    import app as flask_app_module
    current = {'slug': 'x', 'date': '2026-01-01', 'tags': ['unique-tag']}
    posts = [
        current,
        {'slug': 'a', 'date': '2026-02-01', 'tags': ['other']},
        {'slug': 'b', 'date': '2026-03-01', 'tags': ['another']},
    ]
    related = flask_app_module._related_posts(posts, current, limit=3)
    assert {p['slug'] for p in related} == {'a', 'b'}
    # Most recent first within the tie
    assert related[0]['slug'] == 'b'
