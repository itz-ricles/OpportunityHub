-- OpportunityHub schema (SQLite). Kept PostgreSQL-friendly: see documentation/database_design.md.
-- Dates are stored as ISO text (YYYY-MM-DD / YYYY-MM-DD HH:MM:SS, UTC).

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name     TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'student' CHECK (role IN ('student', 'admin')),
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS opportunities (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    title               TEXT NOT NULL,
    category            TEXT NOT NULL CHECK (category IN ('Scholarships', 'Internships', 'Online Courses', 'Competitions')),
    organisation        TEXT NOT NULL,
    location            TEXT NOT NULL,
    geographical_scope  TEXT NOT NULL CHECK (geographical_scope IN ('Local', 'International')),
    description         TEXT NOT NULL,
    eligibility         TEXT NOT NULL,
    funding_information TEXT,
    application_url     TEXT NOT NULL,
    deadline            TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'inactive')),
    created_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS saved_opportunities (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    opportunity_id INTEGER NOT NULL REFERENCES opportunities(id) ON DELETE CASCADE,
    created_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, opportunity_id)
);

CREATE TABLE IF NOT EXISTS applications (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id            INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    opportunity_id     INTEGER NOT NULL REFERENCES opportunities(id) ON DELETE CASCADE,
    application_status TEXT NOT NULL DEFAULT 'Planning'
        CHECK (application_status IN ('Planning', 'Applied', 'Interview', 'Rejected', 'Successful')),
    notes              TEXT,
    created_at         TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at         TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, opportunity_id)
);

CREATE INDEX IF NOT EXISTS idx_opp_category ON opportunities(category);
CREATE INDEX IF NOT EXISTS idx_opp_status_deadline ON opportunities(status, deadline);
CREATE INDEX IF NOT EXISTS idx_saved_user ON saved_opportunities(user_id);
CREATE INDEX IF NOT EXISTS idx_apps_user ON applications(user_id);
