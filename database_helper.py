import os
import sqlite3
import datetime
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv('DATABASE_PATH', 'staging.db')


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
        conn.commit()


def insert_lead(name, email, source='checklist'):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            'INSERT INTO leads (submission, name, email, source) VALUES (?, ?, ?, ?)',
            (datetime.datetime.now().isoformat(), name, email, source)
        )
        conn.commit()


def insert_pageview(path, referrer='', lang='en', user_agent=''):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            'INSERT INTO pageviews (timestamp, path, referrer, lang, user_agent) VALUES (?, ?, ?, ?, ?)',
            (datetime.datetime.now().isoformat(), path, referrer[:500], lang, user_agent[:300])
        )
        conn.commit()


def get_analytics_summary(days=30):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()

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
            (datetime.datetime.now().isoformat(), firstname, lastname, country, email, message)
        )
        conn.commit()
