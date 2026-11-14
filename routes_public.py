"""Pages anyone can see."""
from flask import abort, current_app, g, jsonify, render_template, request

import queries
from constants import CATEGORIES
from db import get_db


def register(app):
    @app.route("/health")
    def health():
        """Used by load balancers. Returns 200 only if the database answers."""
        try:
            get_db().execute("SELECT 1").fetchone()
        except Exception:
            current_app.logger.exception("Health check failed")
            return jsonify(status="unavailable"), 503
        return jsonify(status="ok")

    @app.route("/")
    def index():
        return render_template("index.html", categories=CATEGORIES,
                               featured=queries.featured_opportunities(3))

    @app.route("/opportunities")
    def opportunities():
        q = request.args.get("q", "").strip()
        category = request.args.get("category", "")
        scope = request.args.get("scope", "")
        results = queries.list_opportunities(q=q, category=category, scope=scope)
        return render_template("opportunities.html", results=results, categories=CATEGORIES,
                               q=q, category=category, scope=scope)

    @app.route("/opportunities/<int:opp_id>")
    def opportunity_details(opp_id):
        opp = queries.get_opportunity(opp_id)
        if opp is None:
            abort(404)
        saved = tracked = None
        if g.user:
            saved = queries.is_saved(g.user["id"], opp_id)
            tracked = queries.get_application(g.user["id"], opp_id)
        return render_template("opportunity_details.html", o=opp, is_saved=saved, tracked=tracked)
