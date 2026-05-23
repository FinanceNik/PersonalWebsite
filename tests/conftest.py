"""Test fixtures.

Sets test-mode env vars before importing app so analytics auth is exercised
and the WTF CSRF protection doesn't block POST tests.
"""
import os
import sys
import tempfile

# Test env must be set before app.py is imported.
os.environ.setdefault('FLASK_DEBUG', 'True')
os.environ.setdefault('SECRET_KEY', 'test-secret-do-not-use-anywhere-else')
os.environ.setdefault('ANALYTICS_USER', 'tester')
os.environ.setdefault('ANALYTICS_PASSWORD', 'tester-pass')
os.environ.setdefault('SITE_URL', 'http://localhost')

# Point DB to a temp file so the real staging.db is untouched.
_tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
_tmp.close()
os.environ['DATABASE_PATH'] = _tmp.name

# Make the project root importable when pytest runs from anywhere.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import pytest
import app as flask_app_module


@pytest.fixture
def app():
    flask_app_module.app.config['TESTING'] = True
    # WTF CSRF off in tests so we can POST forms without fetching a token.
    flask_app_module.app.config['WTF_CSRF_ENABLED'] = False
    # Rate limiting off by default so repeated form POSTs don't trip the 5/hour
    # bucket. Tests that exercise the limiter re-enable it locally.
    flask_app_module.limiter.enabled = False
    return flask_app_module.app


@pytest.fixture
def client(app):
    return app.test_client()
