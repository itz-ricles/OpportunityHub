import pytest


@pytest.mark.parametrize("path", ["/", "/login", "/register", "/opportunities", "/opportunities/1"])
def test_public_pages_load(client, path):
    assert client.get(path).status_code == 200


@pytest.mark.parametrize("path", ["/dashboard", "/saved", "/applications", "/account", "/admin", "/admin/students"])
def test_protected_pages_redirect_to_login(client, path):
    res = client.get(path)
    assert res.status_code == 302 and "/login" in res.headers["Location"]


def test_homepage_headline(client):
    assert b"Find Opportunities. Move Forward." in client.get("/").data


def test_error_pages(client):
    assert client.get("/nope").status_code == 404
    assert client.get("/opportunities/9999").status_code == 404
    assert client.post("/").status_code == 405


def test_security_headers(client):
    res = client.get("/")
    assert res.headers["X-Frame-Options"] == "DENY"
    assert "script-src 'self'" in res.headers["Content-Security-Policy"]


def test_private_pages_not_cached(student):
    assert student.get("/dashboard").headers["Cache-Control"] == "private, no-store"
