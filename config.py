"""Central configuration. Secrets come from environment variables, never from source code."""
import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _env_bool(name, default):
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    # SQLite file for local development. Ignored when DATABASE_URL is set.
    DATABASE_PATH = os.environ.get(
        "DATABASE_PATH", str(BASE_DIR / "database" / "opportunityhub.db")
    )
    # PostgreSQL (e.g. Amazon RDS): postgresql://user:password@host:5432/dbname
    DATABASE_URL = os.environ.get("DATABASE_URL") or None
    # Cookie hardening (SESSION_COOKIE_SECURE gets switched on when we add HTTPS)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    CSRF_ENABLED = True
    MAX_CONTENT_LENGTH = 1_000_000  # reject request bodies over ~1 MB
    LOGIN_MAX_ATTEMPTS = 5
    LOGIN_WINDOW_SECONDS = 600
    # How many reverse proxies (load balancer, nginx) sit in front of the app. 0 = none.
    PROXY_COUNT = int(os.environ.get("TRUSTED_PROXY_COUNT", "0"))
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    # Needs HTTPS. Set FORCE_HTTPS=false ONLY for a short HTTP-only demo with no real passwords.
    SESSION_COOKIE_SECURE = _env_bool("FORCE_HTTPS", True)
    PREFERRED_URL_SCHEME = "https"
    SEND_FILE_MAX_AGE_DEFAULT = timedelta(hours=1)


class TestingConfig(Config):
    TESTING = True
    CSRF_ENABLED = False  # one dedicated test turns it on
    SECRET_KEY = "test-secret-not-for-production"
    DATABASE_PATH = str(BASE_DIR / "database" / "test.db")  # tests override this with a temp file
    DATABASE_URL = None  # tests never touch a real PostgreSQL server unless a test asks for it
    PROXY_COUNT = 0


CONFIG_MAP = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
