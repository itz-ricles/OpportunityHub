import os

import pytest
from werkzeug.security import generate_password_hash

import queries
from app import create_app
from db import init_db
from seed import seed_opportunities

PASSWORD = "password123"

# Run the whole suite on PostgreSQL:  TEST_DATABASE_URL=postgresql://user:pw@localhost/ohub_test pytest
TEST_PG = os.environ.get("TEST_DATABASE_URL")


@pytest.fixture
def app(tmp_path):
    """A fresh, seeded database file for every test."""
    cfg = {"DATABASE_PATH": str(tmp_path / "test.db")}
    if TEST_PG:
        # Safety: each test wipes this database, so it must be obviously a throwaway one.
        assert "test" in TEST_PG.rsplit("/", 1)[-1].lower(), "TEST_DATABASE_URL must name a database containing 'test'"
        cfg["DATABASE_URL"] = TEST_PG
    app = create_app("testing", cfg)
    with app.app_context():
        init_db(reset=bool(TEST_PG))
        seed_opportunities()
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def ctx(app):
    """Pushes an app context so tests can call queries.* directly."""
    with app.app_context():
        yield app


@pytest.fixture
def make_user(app):
    def _make(email="ama@example.com", name="Ama Mensah", role="student"):
        with app.app_context():
            return queries.create_user(name, email, generate_password_hash(PASSWORD), role)
    return _make


@pytest.fixture
def login():
    def _login(client, email="ama@example.com", password=PASSWORD, **kwargs):
        return client.post("/login", data={"email": email, "password": password}, **kwargs)
    return _login


@pytest.fixture
def student(app, make_user, login):
    """A logged-in student client."""
    make_user()
    c = app.test_client()
    login(c)
    return c


@pytest.fixture
def admin(app, make_user, login):
    """A logged-in admin client."""
    make_user("boss@example.com", "Kojo Boss", "admin")
    c = app.test_client()
    login(c, "boss@example.com")
    return c
