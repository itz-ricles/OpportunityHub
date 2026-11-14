import pytest

import queries
from constants import APPLICATION_STATUSES, CATEGORY_NAMES, SCOPES
from db import IntegrityErrors, get_db, init_db


def make_user(email="ama@example.com"):
    return queries.create_user("Ama Mensah", email, "fake-hash")


def test_tables_exist(ctx):
    db = get_db()
    if db.backend == "postgres":
        rows = db.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
    else:
        rows = db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    names = {r[0] for r in rows}
    assert {"users", "opportunities", "saved_opportunities", "applications"} <= names


def test_foreign_keys_enforced(ctx):
    with pytest.raises(IntegrityErrors):
        get_db().execute("INSERT INTO saved_opportunities (user_id, opportunity_id) VALUES (999, 999)")


def test_seed_is_idempotent(ctx):
    from seed import seed_opportunities
    assert len(queries.list_opportunities()) == 7
    assert seed_opportunities() == 0
    assert len(queries.list_opportunities()) == 7


def test_seed_covers_required_examples(ctx):
    rows = queries.list_opportunities()
    assert {r["category"] for r in rows} == set(CATEGORY_NAMES)
    assert {r["geographical_scope"] for r in rows} == set(SCOPES)
    assert all("fictional" in r["organisation"].lower() for r in rows)


def test_search_filter_sort(ctx):
    assert [r["title"] for r in queries.list_opportunities(q="cloud")] == ["Demo Cloud Computing Fundamentals"]
    assert queries.list_opportunities(q="accra")[0]["organisation"].startswith("Sample Tech")
    assert queries.list_opportunities(q="sample analytics")  # organisation search
    assert {r["category"] for r in queries.list_opportunities(category="Internships")} == {"Internships"}
    assert {r["geographical_scope"] for r in queries.list_opportunities(scope="Local")} == {"Local"}
    deadlines = [r["deadline"] for r in queries.list_opportunities()]
    assert deadlines == sorted(deadlines)


def test_search_is_injection_safe(ctx):
    assert queries.list_opportunities(q="' OR 1=1 --") == []
    assert queries.list_opportunities(q="%") == []          # wildcard is escaped, not a match-all
    assert len(get_db().execute("SELECT * FROM opportunities").fetchall()) == 7


def test_category_constraint_rejects_unknown(ctx):
    bad = dict(queries.get_opportunity(1), category="Bogus")
    with pytest.raises(IntegrityErrors):
        queries.create_opportunity(bad)


def test_every_constant_value_is_accepted_by_schema(ctx):
    base = dict(queries.get_opportunity(1))
    for cat in CATEGORY_NAMES:
        for scope in SCOPES:
            queries.create_opportunity(dict(base, category=cat, geographical_scope=scope))


def test_duplicate_email_blocked_case_insensitive(ctx):
    assert make_user("Ama@Example.com") is not None
    assert make_user("ama@example.com") is None


def test_invalid_role_rejected(ctx):
    with pytest.raises(ValueError):
        queries.create_user("X", "x@example.com", "h", role="superuser")


def test_save_prevents_duplicates_and_persists(ctx):
    uid = make_user()
    assert queries.save_opportunity(uid, 1) is True
    assert queries.save_opportunity(uid, 1) is False
    assert [r["id"] for r in queries.list_saved(uid)] == [1]
    assert queries.unsave_opportunity(uid, 1) is True
    assert queries.unsave_opportunity(uid, 1) is False
    assert queries.list_saved(uid) == []


def test_cannot_save_hidden_or_missing(ctx):
    uid = make_user()
    queries.set_opportunity_status(2, "inactive")
    with pytest.raises(LookupError):
        queries.save_opportunity(uid, 2)
    with pytest.raises(LookupError):
        queries.save_opportunity(uid, 9999)


def test_tracker_flow(ctx):
    uid = make_user()
    assert queries.track_application(uid, 3) is True
    assert queries.track_application(uid, 3) is False       # no duplicate tracking
    assert queries.list_applications(uid)[0]["application_status"] == "Planning"
    for status in APPLICATION_STATUSES:
        assert queries.update_application_status(uid, 3, status, notes="n") is True
    assert queries.list_applications(uid)[0]["application_status"] == APPLICATION_STATUSES[-1]
    with pytest.raises(ValueError):
        queries.update_application_status(uid, 3, "Hired")


def test_students_cannot_touch_each_others_records(ctx):
    a, b = make_user("a@example.com"), make_user("b@example.com")
    queries.track_application(a, 3)
    queries.save_opportunity(a, 3)
    assert queries.update_application_status(b, 3, "Successful") is False
    assert queries.list_applications(b) == [] and queries.list_saved(b) == []
    assert queries.unsave_opportunity(b, 3) is False
    assert queries.list_applications(a)[0]["application_status"] == "Planning"


def test_admin_crud_and_visibility(ctx):
    new_id = queries.create_opportunity(dict(queries.get_opportunity(1), title="Brand new"))
    assert queries.get_opportunity(new_id) is None                    # draft is hidden from public
    assert queries.set_opportunity_status(new_id, "published")
    assert queries.get_opportunity(new_id)["title"] == "Brand new"
    assert queries.update_opportunity(new_id, {"title": "Renamed", "status": "published; DROP TABLE users"})
    assert queries.get_opportunity(new_id)["title"] == "Renamed"      # non-whitelisted column ignored
    queries.set_opportunity_status(new_id, "inactive")
    assert queries.get_opportunity(new_id) is None
    assert queries.get_opportunity(new_id, published_only=False) is not None
    with pytest.raises(ValueError):
        queries.set_opportunity_status(new_id, "deleted")
    assert queries.delete_opportunity(new_id) is True


def test_deleting_opportunity_cascades(ctx):
    uid = make_user()
    queries.save_opportunity(uid, 1)
    queries.track_application(uid, 1)
    queries.delete_opportunity(1)
    assert queries.list_saved(uid) == [] and queries.list_applications(uid) == []


def test_stats(ctx):
    uid = make_user()
    queries.save_opportunity(uid, 1)
    queries.track_application(uid, 1)
    s = queries.get_stats()
    assert (s["students"], s["published"], s["applications"], s["saved"]) == (1, 7, 1, 1)
    assert dict(s["by_category"])["Scholarships"] == 2


def test_reset_rebuilds_schema(ctx):
    init_db(reset=True)
    assert queries.list_opportunities() == []
