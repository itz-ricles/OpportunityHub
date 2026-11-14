"""Authentication, sessions, role-based access control, account page and admin CLI commands."""
import functools

import click
from flask import abort, current_app, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

import queries
import validation

# Checked when the email doesn't exist, so "unknown email" and "wrong password" take equally long.
DUMMY_HASH = generate_password_hash("not-a-real-password")


def safe_next(target, fallback):
    """Only follow redirects to paths on THIS site (blocks open-redirect attacks)."""
    if target and target.startswith("/") and not target.startswith("//") and "\\" not in target:
        return target
    return fallback


def home_for(user):
    return url_for("admin_dashboard") if user["role"] == "admin" else url_for("dashboard")


def load_user():
    user_id = session.get("user_id")
    g.user = queries.get_user_by_id(user_id) if user_id else None
    if user_id and g.user is None:
        session.clear()  # account was removed; drop the stale session


def _send_to_login():
    flash("Please log in to continue.", "info")
    nxt = request.path if request.method == "GET" else None
    return redirect(url_for("login", next=nxt))


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return _send_to_login()
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return _send_to_login()
        if g.user["role"] != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def register(app):
    app.before_request(load_user)

    @app.context_processor
    def inject_user():
        return {"current_user": g.get("user")}

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if g.user:
            return redirect(home_for(g.user))
        values, errors = {}, {}
        if request.method == "POST":
            values, errors = validation.validate_registration(request.form)
            if not errors:
                # Role is NEVER read from the form: public sign-ups are always students.
                user_id = queries.create_user(values["full_name"], values["email"],
                                              generate_password_hash(values["password"]))
                if user_id is not None:
                    flash("Account created. Please log in.", "success")
                    return redirect(url_for("login"))
                errors["email"] = "That email is already registered. Try logging in instead."
            return render_template("register.html", errors=errors, values=values), 400
        return render_template("register.html", errors=errors, values=values)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if g.user:
            return redirect(home_for(g.user))
        email = ""
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            limiter = current_app.extensions["login_limiter"]
            ip = request.remote_addr or "unknown"
            if limiter.is_blocked(ip, email):
                current_app.logger.warning("Login blocked (too many attempts) ip=%s", ip)
                return render_template(
                    "login.html", email=email,
                    errors={"login": "Too many failed attempts. Please wait a few minutes and try again."}), 429
            user = queries.get_user_by_email(email) if email else None
            hash_to_check = user["password_hash"] if user else DUMMY_HASH
            if check_password_hash(hash_to_check, password) and user is not None:
                limiter.reset(ip, email)
                current_app.logger.info("Login ok user_id=%s", user["id"])
                session.clear()  # fresh session on login (prevents session fixation)
                session["user_id"] = user["id"]
                session.permanent = True
                flash(f"Welcome back, {user['full_name'].split()[0]}.", "success")
                return redirect(safe_next(request.args.get("next"), home_for(user)))
            limiter.record_failure(ip, email)
            current_app.logger.warning("Failed login attempt ip=%s", ip)
            return render_template("login.html", errors={"login": "Incorrect email or password."},
                                   email=email), 401
        return render_template("login.html", errors={}, email=email)

    @app.route("/logout", methods=["POST"])
    def logout():
        session.clear()
        flash("You have been logged out.", "success")
        return redirect(url_for("index"))

    @app.route("/account", methods=["GET", "POST"])
    @login_required
    def account():
        profile_errors, password_errors = {}, {}
        if request.method == "POST":
            if request.form.get("action") == "profile":
                name = request.form.get("full_name", "").strip()
                error = validation.validate_name(name)
                if error:
                    profile_errors["full_name"] = error
                else:
                    queries.update_user_name(g.user["id"], name)
                    flash("Your name has been updated.", "success")
                    return redirect(url_for("account"))
            elif request.form.get("action") == "password":
                if not check_password_hash(g.user["password_hash"], request.form.get("current_password", "")):
                    password_errors["current_password"] = "Your current password is incorrect."
                password_errors.update(validation.validate_password(
                    request.form.get("password", ""), request.form.get("confirm_password", "")))
                if not password_errors:
                    queries.update_user_password(g.user["id"], generate_password_hash(request.form["password"]))
                    flash("Your password has been changed.", "success")
                    return redirect(url_for("account"))
            status = 400 if (profile_errors or password_errors) else 200
            return render_template("account.html", profile_errors=profile_errors,
                                   password_errors=password_errors), status
        return render_template("account.html", profile_errors={}, password_errors={})

    # ----- Admin privileges are only ever granted from the command line on the server -----
    @app.cli.command("create-admin")
    @click.option("--name", prompt="Full name")
    @click.option("--email", prompt="Email")
    @click.password_option()
    def create_admin(name, email, password):
        """Create a new administrator account."""
        values, errors = validation.validate_registration(
            {"full_name": name, "email": email, "password": password, "confirm_password": password})
        if errors:
            raise click.ClickException(" ".join(errors.values()))
        user_id = queries.create_user(values["full_name"], values["email"],
                                      generate_password_hash(password), role="admin")
        if user_id is None:
            raise click.ClickException("That email already exists. Use promote-admin instead.")
        click.echo(f"Administrator {values['email']} created.")

    @app.cli.command("promote-admin")
    @click.argument("email")
    def promote_admin(email):
        """Give an existing account administrator rights."""
        if not queries.set_user_role(email, "admin"):
            raise click.ClickException("No account with that email.")
        click.echo(f"{email} is now an administrator.")
