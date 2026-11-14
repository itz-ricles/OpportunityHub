"""Administrator-only pages. Every route is wrapped in @admin_required."""
from flask import abort, current_app, flash, g, redirect, render_template, request, url_for

import queries
from auth import admin_required
from constants import CATEGORY_NAMES, SCOPES
from validation import validate_opportunity


def _audit(action, opp_id):
    current_app.logger.info("admin_id=%s action=%s opportunity_id=%s", g.user["id"], action, opp_id)


def register(app):
    def _form(values, errors, editing, opp_id=None, status=None):
        return render_template("admin_form.html", v=values, errors=errors, editing=editing,
                               opp_id=opp_id, opp_status=status, category_names=CATEGORY_NAMES, scopes=SCOPES)

    @app.route("/admin")
    @admin_required
    def admin_dashboard():
        return render_template("admin.html", items=queries.list_opportunities(include_all=True),
                               stats=queries.get_stats())

    @app.route("/admin/students")
    @admin_required
    def admin_students():
        return render_template("admin_students.html", students=queries.list_students())

    @app.route("/admin/opportunities/new", methods=["GET", "POST"])
    @admin_required
    def admin_new():
        if request.method == "POST":
            data, errors = validate_opportunity(request.form)
            if errors:
                return _form(request.form, errors, False), 400
            publish = request.form.get("action") == "publish"
            new_id = queries.create_opportunity(data, status="published" if publish else "draft")
            _audit("create", new_id)
            flash("Opportunity published." if publish else "Saved as a draft.", "success")
            return redirect(url_for("admin_dashboard"))
        return _form({}, {}, False)

    @app.route("/admin/opportunities/<int:opp_id>/edit", methods=["GET", "POST"])
    @admin_required
    def admin_edit(opp_id):
        opp = queries.get_opportunity(opp_id, published_only=False)
        if opp is None:
            abort(404)
        if request.method == "POST":
            data, errors = validate_opportunity(request.form)
            if errors:
                return _form(request.form, errors, True, opp_id, opp["status"]), 400
            queries.update_opportunity(opp_id, data)
            _audit("edit", opp_id)
            if request.form.get("action") == "publish":
                queries.set_opportunity_status(opp_id, "published")
            flash("Changes saved.", "success")
            return redirect(url_for("admin_dashboard"))
        return _form(dict(opp), {}, True, opp_id, opp["status"])

    def _set_status(opp_id, status, message):
        if not queries.set_opportunity_status(opp_id, status):
            abort(404)
        _audit(status, opp_id)
        flash(message, "success")
        return redirect(url_for("admin_dashboard"))

    @app.route("/admin/opportunities/<int:opp_id>/publish", methods=["POST"])
    @admin_required
    def admin_publish(opp_id):
        return _set_status(opp_id, "published", "Opportunity published.")

    @app.route("/admin/opportunities/<int:opp_id>/deactivate", methods=["POST"])
    @admin_required
    def admin_deactivate(opp_id):
        return _set_status(opp_id, "inactive", "Opportunity deactivated and hidden from students.")

    @app.route("/admin/opportunities/<int:opp_id>/delete", methods=["POST"])
    @admin_required
    def admin_delete(opp_id):
        if not queries.delete_opportunity(opp_id):
            abort(404)
        _audit("delete", opp_id)
        flash("Opportunity deleted.", "success")
        return redirect(url_for("admin_dashboard"))
