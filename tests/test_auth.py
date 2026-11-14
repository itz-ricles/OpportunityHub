import re

import pytest

import queries
from app import create_app
from db import init_db
from seed import seed_opportunities

GOOD = {"full_name": "Ama Mensah", "email": "ama@example.com", "password": "password123",
        "confirm_password": "password123"}


def test_successful_registration(client, ctx):
    res = client.post("/register", data=GOOD)
    assert res.status_code == 302 and res.headers["Location"].endswith("/login")
    user = queries.get_user_by_email("ama@example.com")
    assert user["role"] == "student"


def test_password_is_hashed_not_plaintext(client, ctx):
    client.post("/register", data=GOOD)
    stored = queries.get_user_by_email("ama@example.com")["password_hash"]
    assert stored != "password123" and "password123" not in stored


def test_duplicate_email(client, make_user):
    make_user("ama@example.com")
    res = client.post("/register", data=GOOD)
    assert res.status_code == 400 and b"already registered" in res.data


@pytest.mark.parametrize("email", ["", "not-an-email", "a@b", "two words@x.com"])
def test_invalid_email(client, email):
    res = client.post("/register", data={**GOOD, "email": email})
    assert res.status_code == 400 and b"email" in res.data.lower()


def test_weak_password(client):
    res = client.post("/register", data={**GOOD, "password": "short", "confirm_password": "short"})
    assert res.status_code == 400 and b"at least 8 characters" in res.data


def test_password_mismatch(client):
    res = client.post("/register", data={**GOOD, "confirm_password": "different123"})
    assert res.status_code == 400 and b"do not match" in res.data


def test_missing_name(client):
    assert client.post("/register", data={**GOOD, "full_name": "  "}).status_code == 400


def test_cannot_register_as_admin(client, ctx):
    client.post("/register", data={**GOOD, "role": "admin"})
    assert queries.get_user_by_email("ama@example.com")["role"] == "student"


def test_login_success(client, make_user, login):
    make_user()
    res = login(client)
    assert res.status_code == 302 and res.headers["Location"].endswith("/dashboard")
    assert client.get("/dashboard").status_code == 200


def test_wrong_password_and_unknown_email_look_identical(client, make_user, login):
    make_user()
    wrong = login(client, password="nope-nope-nope")
    unknown = login(client, email="ghost@example.com")
    assert wrong.status_code == unknown.status_code == 401
    assert b"Incorrect email or password" in wrong.data and b"Incorrect email or password" in unknown.data


def test_logout(student):
    assert student.post("/logout").status_code == 302
    assert student.get("/dashboard").status_code == 302


def test_logout_requires_post(student):
    assert student.get("/logout").status_code == 405


def test_open_redirect_blocked(client, make_user, login):
    make_user()
    for bad in ["//evil.com", "https://evil.com", "/\\evil.com"]:
        c = client.application.test_client()
        res = c.post(f"/login?next={bad}", data={"email": "ama@example.com", "password": "password123"})
        assert "evil.com" not in res.headers["Location"]


def test_next_redirect_works_for_local_paths(client, make_user, login):
    make_user()
    res = client.post("/login?next=/saved", data={"email": "ama@example.com", "password": "password123"})
    assert res.headers["Location"].endswith("/saved")


def test_account_update_name_and_password(student, app, login):
    assert student.post("/account", data={"action": "profile", "full_name": "Ama K. Mensah"}).status_code == 302
    bad = student.post("/account", data={"action": "password", "current_password": "wrong",
                                         "password": "newpassword1", "confirm_password": "newpassword1"})
    assert bad.status_code == 400 and b"current password is incorrect" in bad.data
    ok = student.post("/account", data={"action": "password", "current_password": "password123",
                                        "password": "newpassword1", "confirm_password": "newpassword1"})
    assert ok.status_code == 302
    fresh = app.test_client()
    assert login(fresh, password="newpassword1").status_code == 302
    with app.app_context():
        assert queries.get_user_by_email("ama@example.com")["full_name"] == "Ama K. Mensah"


def test_csrf_blocks_forged_posts(tmp_path):
    app = create_app("testing", {"DATABASE_PATH": str(tmp_path / "c.db"), "CSRF_ENABLED": True})
    with app.app_context():
        init_db()
    client = app.test_client()
    assert client.post("/register", data=GOOD).status_code == 400          # no token
    token = re.search(rb'name="csrf_token" value="([^"]+)"', client.get("/register").data).group(1).decode()
    ok = client.post("/register", data={**GOOD, "csrf_token": token})
    assert ok.status_code == 302


def test_create_admin_cli(app):
    runner = app.test_cli_runner()
    res = runner.invoke(args=["create-admin"], input="Kojo Boss\nboss@example.com\npassword123\npassword123\n")
    assert res.exit_code == 0, res.output
    with app.app_context():
        assert queries.get_user_by_email("boss@example.com")["role"] == "admin"


def test_promote_admin_cli(app, make_user):
    make_user("ama@example.com")
    runner = app.test_cli_runner()
    assert runner.invoke(args=["promote-admin", "ama@example.com"]).exit_code == 0
    assert runner.invoke(args=["promote-admin", "ghost@example.com"]).exit_code != 0
    with app.app_context():
        assert queries.get_user_by_email("ama@example.com")["role"] == "admin"
