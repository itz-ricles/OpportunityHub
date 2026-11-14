"""Logged-in student features. Every query is scoped to g.user, so nobody can reach another student's data."""
from flask import abort, flash, g, redirect, render_template, request, url_for

import queries
from auth import login_required, safe_next
from constants import APPLICATION_STATUSES


def register(app):
    @app.route("/dashboard")
    @login_required
    def dashboard():
        uid = g.user["id"]
        return render_template(
            "dashboard.html", saved_count=queries.count_saved(uid),
            tracked_count=queries.count_applications(uid),
            recent=queries.list_applications(uid)[:5], upcoming=queries.upcoming_deadlines(uid))

    @app.route("/saved")
    @login_required
    def saved():
        return render_template("saved.html", items=queries.list_saved(g.user["id"]))

    @app.route("/applications")
    @login_required
    def applications():
        return render_template("applications.html", items=queries.list_applications(g.user["id"]),
                               statuses=APPLICATION_STATUSES)

    def _back(opp_id):
        return redirect(safe_next(request.form.get("next"), url_for("opportunity_details", opp_id=opp_id)))

    @app.route("/opportunities/<int:opp_id>/save", methods=["POST"])
    @login_required
    def save_opp(opp_id):
        try:
            created = queries.save_opportunity(g.user["id"], opp_id)
        except LookupError:
            abort(404)
        flash("Saved to your list." if created else "You already saved this opportunity.", "success")
        return _back(opp_id)

    @app.route("/opportunities/<int:opp_id>/unsave", methods=["POST"])
    @login_required
    def unsave_opp(opp_id):
        queries.unsave_opportunity(g.user["id"], opp_id)
        flash("Removed from your saved list.", "success")
        return _back(opp_id)

    @app.route("/opportunities/<int:opp_id>/track", methods=["POST"])
    @login_required
    def track_app(opp_id):
        try:
            created = queries.track_application(g.user["id"], opp_id)
        except LookupError:
            abort(404)
        flash("Added to your tracker." if created else "You are already tracking this opportunity.", "success")
        return _back(opp_id)

    @app.route("/applications/<int:opp_id>/status", methods=["POST"])
    @login_required
    def set_app_status(opp_id):
        status = request.form.get("application_status", "")
        notes = request.form.get("notes", "").strip()[:1000]
        try:
            updated = queries.update_application_status(g.user["id"], opp_id, status, notes=notes)
        except ValueError:
            flash("Choose a valid status.", "error")
            return redirect(url_for("applications"))
        if not updated:
            abort(404)  # not tracked by THIS student
        flash("Tracker updated.", "success")
        return redirect(url_for("applications"))
