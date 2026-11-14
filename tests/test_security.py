import pytest

import queries
from app import create_app
from db import init_db
from ratelimit import LoginLimiter
from test_opportunities import NEW

PAYLOADS = ["' OR '1'='1", "'; DROP TABLE users; --", "\" OR 1=1 --", "%' UNION SELECT password_hash FROM users --",
            "<script>alert(1)</script>", "\x00", "A" * 5000, "%", "_"]


@pytest.mark.parametrize("payload", PAYLOADS)
def test_sql_injection_and_junk_on_public_inputs(client, student, ctx, payload):
    for url in ("/opportunities", "/login", "/register"):
        pass
    for key in ("q", "category", "scope"):
        assert client.get("/opportunities", query_string={key: payload}).status_code in (200, 400)  # 400 only for NUL bytes
    assert client.post("/login", data={"email": payload, "password": payload}).status_code in (400, 401, 429)
    assert client.post("/register", data={"full_name": payload, "email": payload, "password": payload,
                                          "confirm_password": payload}).status_code == 400
    assert queries.get_user_by_email("ama@example.com") is not None          # users table still intact
    assert len(queries.list_opportunities()) == 7


@pytest.mark.parametrize("payload", PAYLOADS)
def test_injection_in_admin_and_tracker_inputs(admin, student, ctx, payload):
    res = admin.post("/admin/opportunities/new", data={**NEW, "title": payload, "organisation": payload})
    assert res.status_code in (302, 400)
    student.post("/opportunities/1/track")
    student.post("/applications/1/status", data={"application_status": payload, "notes": payload})
    assert len(queries.list_opportunities(include_all=True)) >= 7


def test_stored_xss_is_escaped_everywhere(app, make_user, login, admin):
    evil = "<img src=x onerror=alert(1)>"
    make_user("x@example.com", evil)
    victim = app.test_client()
    login(victim, "x@example.com")
    for page in (victim.get("/dashboard").data, victim.get("/account").data, admin.get("/admin/students").data):
        assert b"<img src=x" not in page and b"&lt;img" in page


def test_session_cookie_flags(client, make_user, login):
    make_user()
    cookie = login(client).headers.get("Set-Cookie", "")
    assert "HttpOnly" in cookie and "SameSite=Lax" in cookie


def test_session_is_reset_on_login(client, make_user, login):
    make_user()
    client.get("/login")
    with client.session_transaction() as s:
        before = s["_csrf"]
    login(client)
    with client.session_transaction() as s:
        assert s.get("_csrf") != before and "user_id" in s


def test_role_cannot_be_changed_through_account_form(student, ctx):
    student.post("/account", data={"action": "profile", "full_name": "Ama", "role": "admin"})
    assert queries.get_user_by_email("ama@example.com")["role"] == "student"
    assert student.get("/admin").status_code == 403


def test_login_rate_limit_blocks_even_correct_password(client, make_user, login):
    make_user()
    for _ in range(5):
        assert login(client, password="wrong-password").status_code == 401
    assert login(client).status_code == 429
    other_ip = client.application.test_client()
    assert other_ip.post("/login", data={"email": "ama@example.com", "password": "password123"},
                         environ_base={"REMOTE_ADDR": "10.0.0.9"}).status_code == 302


def test_limiter_window_and_reset():
    now = [0.0]
    lim = LoginLimiter(max_attempts=3, window_seconds=60, clock=lambda: now[0])
    for _ in range(3):
        lim.record_failure("1.1.1.1", "a@x.com")
    assert lim.is_blocked("1.1.1.1", "a@x.com") and not lim.is_blocked("1.1.1.1", "b@x.com")
    now[0] = 61
    assert not lim.is_blocked("1.1.1.1", "a@x.com")          # window expired
    for _ in range(3):
        lim.record_failure("1.1.1.1", "a@x.com")
    lim.reset("1.1.1.1", "a@x.com")
    assert not lim.is_blocked("1.1.1.1", "a@x.com")


def test_ip_wide_limit_stops_email_rotation():
    lim = LoginLimiter(max_attempts=2, window_seconds=60)
    for i in range(8):
        lim.record_failure("2.2.2.2", f"user{i}@x.com")
    assert lim.is_blocked("2.2.2.2", "fresh@x.com")


def test_oversized_request_rejected(client):
    assert client.post("/login", data={"email": "x" * 2_000_000, "password": "y"}).status_code == 413


def test_production_refuses_weak_secret(tmp_path):
    db = str(tmp_path / "p.db")
    for weak in ("short", "change-me-" + "x" * 40):
        with pytest.raises(RuntimeError):
            create_app("production", {"SECRET_KEY": weak, "DATABASE_PATH": db})


def test_production_cookies_and_hsts(tmp_path, make_user=None):
    app = create_app("production", {"SECRET_KEY": "k" * 48, "DATABASE_PATH": str(tmp_path / "p.db"),
                                    "DATABASE_URL": None})
    with app.app_context():
        init_db()
    res = app.test_client().get("/")
    assert "max-age=31536000" in res.headers["Strict-Transport-Security"]
    assert app.config["SESSION_COOKIE_SECURE"] is True and app.config["DEBUG"] is False
