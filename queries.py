"""All SQL lives here. Every query is parameterised (never string-formatted with user input).

The Database wrapper in db.py hides the SQLite / PostgreSQL differences (placeholders, ILIKE, new-row ids)."""
import sqlite3
from datetime import date, datetime, timezone

from constants import (APPLICATION_STATUSES, CATEGORY_NAMES, OPPORTUNITY_STATUSES, ROLES)
from db import get_db

OPPORTUNITY_FIELDS = (
    "title", "category", "organisation", "location", "geographical_scope",
    "description", "eligibility", "funding_information", "application_url", "deadline",
)


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _like(term):
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


# ---------- users ----------
def create_user(full_name, email, password_hash, role="student"):
    """Returns the new id, or None if the email is already registered."""
    if role not in ROLES:
        raise ValueError(f"Invalid role: {role}")
    db = get_db()
    user_id = db.insert_returning_id(
        "INSERT INTO users (full_name, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(email) DO NOTHING",
        (full_name, email.strip().lower(), password_hash, role, _now()),
    )
    db.commit()
    return user_id


def get_user_by_email(email):
    return get_db().execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),)).fetchone()


def get_user_by_id(user_id):
    return get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def set_user_role(email, role):
    """Only called from the command line (create-admin / promote-admin), never from a web form."""
    if role not in ROLES:
        raise ValueError(f"Invalid role: {role}")
    db = get_db()
    cur = db.execute("UPDATE users SET role = ? WHERE email = ?", (role, email.strip().lower()))
    db.commit()
    return cur.rowcount > 0


def update_user_name(user_id, full_name):
    db = get_db()
    db.execute("UPDATE users SET full_name = ? WHERE id = ?", (full_name, user_id))
    db.commit()


def update_user_password(user_id, password_hash):
    db = get_db()
    db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))
    db.commit()


def list_students():
    return get_db().execute(
        "SELECT u.id, u.full_name, u.email, u.created_at, "
        "(SELECT COUNT(*) FROM saved_opportunities s WHERE s.user_id = u.id) AS saved_count, "
        "(SELECT COUNT(*) FROM applications a WHERE a.user_id = u.id) AS tracked_count "
        "FROM users u WHERE u.role = 'student' ORDER BY u.created_at DESC, u.id DESC").fetchall()


# ---------- opportunities ----------
def list_opportunities(q="", category="", scope="", include_all=False):
    db = get_db()
    sql = "SELECT * FROM opportunities WHERE 1 = 1"
    params = []
    if not include_all:
        sql += " AND status = 'published'"
    if q:
        like = db.like  # LIKE on SQLite, ILIKE on PostgreSQL (both case-insensitive)
        sql += (" AND (title " + like + " ? ESCAPE '\\' OR organisation " + like + " ? ESCAPE '\\'"
                " OR location " + like + " ? ESCAPE '\\')")
        params += [_like(q)] * 3
    if category:
        sql += " AND category = ?"
        params.append(category)
    if scope:
        sql += " AND geographical_scope = ?"
        params.append(scope)
    sql += " ORDER BY deadline ASC, id ASC"
    return db.execute(sql, params).fetchall()


def featured_opportunities(limit=3):
    """'Featured' = published listings with the nearest deadlines (no separate flag yet)."""
    return list_opportunities()[:limit]


def get_opportunity(opp_id, published_only=True):
    sql = "SELECT * FROM opportunities WHERE id = ?"
    if published_only:
        sql += " AND status = 'published'"
    return get_db().execute(sql, (opp_id,)).fetchone()


# Note: the f-strings below only interpolate column names from OPPORTUNITY_FIELDS (a fixed whitelist);
# every value is passed as a bound parameter.
def create_opportunity(data, status="draft"):
    if status not in OPPORTUNITY_STATUSES:
        raise ValueError(f"Invalid status: {status}")
    db = get_db()
    now = _now()
    new_id = db.insert_returning_id(
        f"INSERT INTO opportunities ({', '.join(OPPORTUNITY_FIELDS)}, status, created_at, updated_at) "  # nosec B608
        f"VALUES ({', '.join('?' for _ in OPPORTUNITY_FIELDS)}, ?, ?, ?)",
        [data.get(f) for f in OPPORTUNITY_FIELDS] + [status, now, now],
    )
    db.commit()
    return new_id


def update_opportunity(opp_id, data):
    """Only whitelisted columns can be changed. Returns True if a row was updated."""
    fields = [f for f in OPPORTUNITY_FIELDS if f in data]
    if not fields:
        return False
    db = get_db()
    cur = db.execute(
        f"UPDATE opportunities SET {', '.join(f + ' = ?' for f in fields)}, updated_at = ? WHERE id = ?",  # nosec B608
        [data[f] for f in fields] + [_now(), opp_id],
    )
    db.commit()
    return cur.rowcount > 0


def set_opportunity_status(opp_id, status):
    if status not in OPPORTUNITY_STATUSES:
        raise ValueError(f"Invalid status: {status}")
    db = get_db()
    cur = db.execute("UPDATE opportunities SET status = ?, updated_at = ? WHERE id = ?",
                     (status, _now(), opp_id))
    db.commit()
    return cur.rowcount > 0


def delete_opportunity(opp_id):
    db = get_db()
    cur = db.execute("DELETE FROM opportunities WHERE id = ?", (opp_id,))
    db.commit()
    return cur.rowcount > 0


# ---------- saved opportunities ----------
def save_opportunity(user_id, opp_id):
    """True if newly saved, False if it was already saved. LookupError if the listing isn't available."""
    if get_opportunity(opp_id) is None:
        raise LookupError("Opportunity not found")
    db = get_db()
    cur = db.execute(
        "INSERT INTO saved_opportunities (user_id, opportunity_id, created_at) VALUES (?, ?, ?) "
        "ON CONFLICT(user_id, opportunity_id) DO NOTHING",
        (user_id, opp_id, _now()),
    )
    db.commit()
    return cur.rowcount == 1


def unsave_opportunity(user_id, opp_id):
    db = get_db()
    cur = db.execute("DELETE FROM saved_opportunities WHERE user_id = ? AND opportunity_id = ?",
                     (user_id, opp_id))
    db.commit()
    return cur.rowcount > 0


def is_saved(user_id, opp_id):
    return get_db().execute(
        "SELECT 1 FROM saved_opportunities WHERE user_id = ? AND opportunity_id = ?",
        (user_id, opp_id)).fetchone() is not None


def list_saved(user_id):
    return get_db().execute(
        "SELECT o.*, s.created_at AS saved_at FROM saved_opportunities s "
        "JOIN opportunities o ON o.id = s.opportunity_id "
        "WHERE s.user_id = ? ORDER BY s.created_at DESC, s.id DESC", (user_id,)).fetchall()


# ---------- application tracker (records the student's own progress only) ----------
def track_application(user_id, opp_id, status="Planning"):
    """True if newly tracked, False if already tracked."""
    if status not in APPLICATION_STATUSES:
        raise ValueError(f"Invalid status: {status}")
    if get_opportunity(opp_id) is None:
        raise LookupError("Opportunity not found")
    db = get_db()
    now = _now()
    cur = db.execute(
        "INSERT INTO applications (user_id, opportunity_id, application_status, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?) ON CONFLICT(user_id, opportunity_id) DO NOTHING",
        (user_id, opp_id, status, now, now),
    )
    db.commit()
    return cur.rowcount == 1


def update_application_status(user_id, opp_id, status, notes=None):
    """Filters by user_id, so a student can only ever touch their own records."""
    if status not in APPLICATION_STATUSES:
        raise ValueError(f"Invalid status: {status}")
    db = get_db()
    if notes is None:
        cur = db.execute(
            "UPDATE applications SET application_status = ?, updated_at = ? "
            "WHERE user_id = ? AND opportunity_id = ?", (status, _now(), user_id, opp_id))
    else:
        cur = db.execute(
            "UPDATE applications SET application_status = ?, notes = ?, updated_at = ? "
            "WHERE user_id = ? AND opportunity_id = ?", (status, notes, _now(), user_id, opp_id))
    db.commit()
    return cur.rowcount > 0


def list_applications(user_id):
    return get_db().execute(
        "SELECT o.*, a.application_status, a.notes, a.updated_at AS last_updated "
        "FROM applications a JOIN opportunities o ON o.id = a.opportunity_id "
        "WHERE a.user_id = ? ORDER BY a.updated_at DESC, a.id DESC", (user_id,)).fetchall()


def get_application(user_id, opp_id):
    return get_db().execute(
        "SELECT * FROM applications WHERE user_id = ? AND opportunity_id = ?", (user_id, opp_id)).fetchone()


def count_saved(user_id):
    return get_db().execute("SELECT COUNT(*) FROM saved_opportunities WHERE user_id = ?", (user_id,)).fetchone()[0]


def count_applications(user_id):
    return get_db().execute("SELECT COUNT(*) FROM applications WHERE user_id = ?", (user_id,)).fetchone()[0]


def upcoming_deadlines(user_id, limit=5, today=None):
    """Published listings the student saved, or is still planning/applying for, that haven't closed."""
    today = today or date.today().isoformat()
    return get_db().execute(
        "SELECT * FROM opportunities WHERE status = 'published' AND deadline >= ? AND ("
        " id IN (SELECT opportunity_id FROM saved_opportunities WHERE user_id = ?)"
        " OR id IN (SELECT opportunity_id FROM applications WHERE user_id = ?"
        "           AND application_status IN ('Planning', 'Applied'))"
        ") ORDER BY deadline ASC LIMIT ?", (today, user_id, user_id, limit)).fetchall()


# ---------- statistics ----------
def get_stats():
    db = get_db()
    scalar = lambda sql: db.execute(sql).fetchone()[0]
    per_cat = {r["category"]: r["n"] for r in db.execute(
        "SELECT category, COUNT(*) AS n FROM opportunities WHERE status = 'published' GROUP BY category")}
    per_status = {r["application_status"]: r["n"] for r in db.execute(
        "SELECT application_status, COUNT(*) AS n FROM applications GROUP BY application_status")}
    return {
        "students": scalar("SELECT COUNT(*) FROM users WHERE role = 'student'"),
        "published": scalar("SELECT COUNT(*) FROM opportunities WHERE status = 'published'"),
        "total_opportunities": scalar("SELECT COUNT(*) FROM opportunities"),
        "applications": scalar("SELECT COUNT(*) FROM applications"),
        "saved": scalar("SELECT COUNT(*) FROM saved_opportunities"),
        "by_category": [(name, per_cat.get(name, 0)) for name in CATEGORY_NAMES],
        "by_status": [(st, per_status.get(st, 0)) for st in APPLICATION_STATUSES],
    }
