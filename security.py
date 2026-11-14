"""CSRF protection and browser security headers."""
import hmac
import secrets

from flask import abort, current_app, g, request, session


def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(16)
    return session["_csrf"]


def reject_nul_bytes():
    """PostgreSQL cannot store NUL (0x00) characters and would crash with a 500; no real user types one."""
    for source in (request.args, request.form):
        for _key, value in source.items(multi=True):
            if "\x00" in value:
                abort(400)


def protect_from_csrf():
    if not current_app.config.get("CSRF_ENABLED", True):
        return
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        sent = request.form.get("csrf_token", "").encode()
        expected = session.get("_csrf", "").encode()
        if not expected or not hmac.compare_digest(sent, expected):
            abort(400)


CSP = ("default-src 'self'; style-src 'self' https://fonts.googleapis.com; "
       "font-src https://fonts.gstatic.com; img-src 'self' data:; script-src 'self'; "
       "frame-ancestors 'none'; form-action 'self'; base-uri 'self'")


def add_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Content-Security-Policy", CSP)
    if current_app.config.get("SESSION_COOKIE_SECURE"):  # production only (needs HTTPS)
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    if g.get("user") is not None:  # stop the back button showing private pages after logout
        response.headers["Cache-Control"] = "private, no-store"
    return response


def init_app(app):
    app.before_request(reject_nul_bytes)
    app.before_request(protect_from_csrf)
    app.after_request(add_security_headers)
    app.jinja_env.globals["csrf_token"] = csrf_token
