"""OpportunityHub application entry point (application factory pattern)."""
import logging
import os
from datetime import date

from flask import Flask, render_template
from werkzeug.middleware.proxy_fix import ProxyFix

import auth
import db
import routes_admin
import routes_public
import routes_student
import security
from config import CONFIG_MAP
from ratelimit import LoginLimiter


def create_app(config_name=None, test_config=None):
    # Safe by default: if FLASK_ENV is missing we run as production (no debug mode).
    config_name = config_name or os.environ.get("FLASK_ENV", "production")
    app = Flask(__name__)
    app.config.from_object(CONFIG_MAP.get(config_name, CONFIG_MAP["development"]))
    if test_config:
        app.config.update(test_config)

    secret = app.config.get("SECRET_KEY")
    if not secret:
        raise RuntimeError("SECRET_KEY is not set. Copy .env.example to .env and set a real value.")
    if config_name == "production" and (len(secret) < 32 or secret.startswith("change-me")):
        raise RuntimeError("Production needs a strong SECRET_KEY (32+ random characters).")

    app.logger.setLevel(app.config["LOG_LEVEL"])  # stderr output is what CloudWatch collects on AWS
    if app.config["PROXY_COUNT"] > 0:  # trust X-Forwarded-* headers from exactly this many proxies
        n = app.config["PROXY_COUNT"]
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=n, x_proto=n, x_host=n)
    if config_name == "production" and not app.config.get("DATABASE_URL"):
        app.logger.warning("Production is using SQLite: data is lost when the server is replaced. Set DATABASE_URL.")

    app.extensions["login_limiter"] = LoginLimiter(
        app.config["LOGIN_MAX_ATTEMPTS"], app.config["LOGIN_WINDOW_SECONDS"])
    app.jinja_env.globals["is_closed"] = lambda deadline: deadline < date.today().isoformat()

    db.init_app(app)
    security.init_app(app)
    auth.register(app)
    routes_public.register(app)
    routes_student.register(app)
    routes_admin.register(app)
    register_error_handlers(app)
    return app


ERRORS = {
    400: ("Request rejected", "Your session may have expired. Go back, refresh the page and try again."),
    403: ("Access denied", "You do not have permission to view this page."),
    404: ("Page not found", "That page does not exist or has moved."),
    405: ("Method not allowed", "That action is not available on this page."),
    413: ("Request too large", "The data you sent was too large."),
    429: ("Too many requests", "Please slow down and try again in a few minutes."),
    500: ("Something went wrong", "An unexpected error occurred. Please try again later."),
}


def register_error_handlers(app):
    def make_handler(code):
        title, message = ERRORS[code]
        return lambda _e: (render_template("error.html", code=code, title=title, message=message), code)

    for code in ERRORS:
        app.register_error_handler(code, make_handler(code))


if __name__ == "__main__":
    create_app().run()
