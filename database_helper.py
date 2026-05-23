"""SQLite helpers: schema, inserts, analytics, retention.

Timestamps are stored as naive ISO strings whose value is always UTC. We
keep them naive (no `+00:00` suffix) so existing rows — which were inserted
with the old naive `datetime.now()` — sort consistently against new ones in
plain string comparisons. The Python-side helpers convert from tz-aware to
naive ISO so the storage format never changes.

Pageview rows accumulate forever without help; `prune_old_pageviews()` drops
rows older than the retention window. `insert_pageview` runs the prune with
1% probability so the table stays bounded without requiring a cron.
"""
import datetime
import os
import random
import sqlite3
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv('DATABASE_PATH', 'staging.db')

# Default retention for pageviews. Overridable via env so tests / ops can tune.
PAGEVIEW_RETENTION_DAYS = int(os.getenv('PAGEVIEW_RETENTION_DAYS', '90'))
# Probability that any given insert also runs the prune. 1% keeps the table
# bounded without piling all the work on a single request.
_AUTO_PRUNE_PROBABILITY = 0.01


def _utc_now_iso():
    """Current UTC time as a naive ISO string ('2026-05-23T14:30:00.123456').

    Naive on the wire so it sorts cleanly against legacy rows that were
    written with the old `datetime.datetime.now()` (server-local, naive).
    """
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat()


def _utc_cutoff_iso(days):
    """ISO string for `now - days`, in the same naive-UTC format as stored rows."""
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
    return cutoff.replace(tzinfo=None).isoformat()


def create_database():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS contactRequests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                submission TEXT NOT NULL,
                firstname TEXT NOT NULL,
                lastname TEXT NOT NULL,
                country TEXT NOT NULL,
                email TEXT NOT NULL,
                message TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS pageviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                path TEXT NOT NULL,
                referrer TEXT,
                lang TEXT,
                user_agent TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                submission TEXT NOT NULL,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                source TEXT NOT NULL
            )
        ''')
        # Indexes — all analytics queries filter on `pageviews.timestamp`, then
        # GROUP BY path / lang / DATE(timestamp). Without these we full-scan
        # every analytics page load.
        conn.execute('CREATE INDEX IF NOT EXISTS idx_pageviews_ts ON pageviews(timestamp)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_pageviews_path ON pageviews(path)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_contact_submission ON contactRequests(submission)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_leads_submission ON leads(submission)')
        conn.commit()


def insert_lead(name, email, source='checklist'):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            'INSERT INTO leads (submission, name, email, source) VALUES (?, ?, ?, ?)',
            (_utc_now_iso(), name, email, source)
        )
        conn.commit()


def insert_pageview(path, referrer='', lang='en', user_agent=''):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            'INSERT INTO pageviews (timestamp, path, referrer, lang, user_agent) VALUES (?, ?, ?, ?, ?)',
            (_utc_now_iso(), path, referrer[:500], lang, user_agent[:300])
        )
        conn.commit()
    # Opportunistic retention so the table doesn't grow forever.
    if random.random() < _AUTO_PRUNE_PROBABILITY:
        try:
            prune_old_pageviews()
        except Exception:
            pass


def prune_old_pageviews(days=None):
    """Delete pageview rows older than `days` (default PAGEVIEW_RETENTION_DAYS).

    Returns the row count deleted. Safe to call from a cron or on-demand.
    """
    if days is None:
        days = PAGEVIEW_RETENTION_DAYS
    cutoff = _utc_cutoff_iso(days)
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute('DELETE FROM pageviews WHERE timestamp < ?', (cutoff,))
        deleted = cur.rowcount
        conn.commit()
        return deleted


def get_analytics_summary(days=30):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cutoff = _utc_cutoff_iso(days)

        total = conn.execute('SELECT COUNT(*) as c FROM pageviews WHERE timestamp > ?', (cutoff,)).fetchone()['c']
        by_page = conn.execute(
            'SELECT path, COUNT(*) as views FROM pageviews WHERE timestamp > ? GROUP BY path ORDER BY views DESC LIMIT 20',
            (cutoff,)
        ).fetchall()
        by_lang = conn.execute(
            'SELECT lang, COUNT(*) as views FROM pageviews WHERE timestamp > ? GROUP BY lang ORDER BY views DESC',
            (cutoff,)
        ).fetchall()
        by_day = conn.execute(
            'SELECT DATE(timestamp) as day, COUNT(*) as views FROM pageviews WHERE timestamp > ? GROUP BY DATE(timestamp) ORDER BY day DESC LIMIT 30',
            (cutoff,)
        ).fetchall()
        by_referrer = conn.execute(
            "SELECT referrer, COUNT(*) as views FROM pageviews WHERE timestamp > ? AND referrer != '' GROUP BY referrer ORDER BY views DESC LIMIT 10",
            (cutoff,)
        ).fetchall()

        return {
            'total': total,
            'by_page': [dict(r) for r in by_page],
            'by_lang': [dict(r) for r in by_lang],
            'by_day': [dict(r) for r in by_day],
            'by_referrer': [dict(r) for r in by_referrer],
        }


def insert_contact_request(firstname, lastname, country, email, message):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            'INSERT INTO contactRequests (submission, firstname, lastname, country, email, message) VALUES (?, ?, ?, ?, ?, ?)',
            (_utc_now_iso(), firstname, lastname, country, email, message)
        )
        conn.commit()
