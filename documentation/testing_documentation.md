# OpportunityHub: Testing Documentation

## 1. Strategy
| Level | What it checks | How |
|---|---|---|
| Unit / database | SQL functions, constraints, ownership rules (runs on SQLite and PostgreSQL) | `tests/test_database.py` |
| Deployment readiness | Health check, production defaults, proxy handling, logging, database wrapper | `tests/test_deploy.py` |
| Feature | Authentication, listings, bookmarks, tracker, admin tools | `test_auth.py`, `test_opportunities.py`, `test_applications.py`, `test_admin.py` |
| Integration | Whole user journeys across features | `test_integration.py`, `test_smoke.py` |
| Security | Injection, XSS, CSRF, sessions, rate limiting, production settings | `test_security.py`, plus `bandit` and `pip-audit` |
| Accessibility (structure) | Labels, lang, viewport, one h1, unique ids, button names | `test_accessibility.py` |
| Manual | Layout, browsers, devices, keyboard, screen readers | `manual_test_checklist.md` |

Each test runs against its own fresh, seeded temporary database, so tests never affect each other or real data.

## 2. How to run
```
pip install -r requirements-dev.txt
pytest                              # full suite
pytest tests/test_auth.py -v        # one file, verbose
bandit -r . -x ./tests -s B105      # static security scan
pip-audit -r requirements.txt       # dependency vulnerabilities
```

## 3. Latest automated results
Run on 13 November 2026, Python 3.12.3, Flask 3.1.3, PostgreSQL 16.15, psycopg 3.3.9, gunicorn 27.0.1.

| Check | Result |
|---|---|
| `pytest` on SQLite | **150 passed, 0 failed** |
| `pytest` on PostgreSQL 16 (`TEST_DATABASE_URL`) | **150 passed, 0 failed** |
| Production smoke test | gunicorn + PostgreSQL: health check, search, admin login, security headers all OK |
| SQLite to PostgreSQL migration | Tested: data, logins, notes kept; id counters continue correctly; second run refuses |
| `bandit` (B105 skipped, see note) | No issues reported |
| `pip-audit` | No known vulnerabilities |

Note on B105: bandit flags error-message strings such as "Enter a password." as possible hard-coded passwords. These are false positives, so that rule is skipped.

| Test file | Tests |
|---|---|
| test_accessibility.py | 16 |
| test_admin.py | 18 |
| test_applications.py | 9 |
| test_auth.py | 21 |
| test_database.py | 18 |
| test_deploy.py | 13 |
| test_integration.py | 4 |
| test_opportunities.py | 8 |
| test_security.py | 28 |
| test_smoke.py | 15 |
| **Total** | **150** |

(Parametrised tests count once per parameter, so 150 is the number of executed cases.)

## 4. Requirement traceability
### Authentication
| Required test case | Automated test | Result |
|---|---|---|
| Successful registration | `test_auth::test_successful_registration` | Pass |
| Duplicate email registration | `test_auth::test_duplicate_email` | Pass |
| Invalid email | `test_auth::test_invalid_email` | Pass |
| Weak password | `test_auth::test_weak_password` | Pass |
| Successful login | `test_auth::test_login_success` | Pass |
| Incorrect password | `test_auth::test_wrong_password_and_unknown_email_look_identical` | Pass |
| Logout | `test_auth::test_logout`, `test_logout_requires_post` | Pass |
| Unauthenticated page access | `test_smoke::test_protected_pages_redirect_to_login` | Pass |

### Opportunities
| Required test case | Automated test | Result |
|---|---|---|
| Create an opportunity | `test_opportunities::test_admin_created_listing_appears_publicly` | Pass |
| Display opportunities | `test_opportunities::test_listing_page_shows_real_records` | Pass |
| Search opportunities | `test_opportunities::test_search_and_filters`, `test_database::test_search_filter_sort` | Pass |
| Filter by category | `test_opportunities::test_search_and_filters` | Pass |
| View opportunity details | `test_opportunities::test_details_page_and_safe_external_link` | Pass |
| Official external links | same test (checks the official URL and `rel="noopener noreferrer"`) | Pass |

### Student functionality
| Required test case | Automated test | Result |
|---|---|---|
| Save an opportunity | `test_applications::test_save_unsave_and_no_duplicates` | Pass |
| Prevent duplicate bookmarks | same test; `test_database::test_save_prevents_duplicates_and_persists` | Pass |
| Remove saved opportunities | `test_applications::test_save_unsave_and_no_duplicates` | Pass |
| Add application to tracker | `test_applications::test_track_and_update_status` | Pass |
| Update application status | `test_applications::test_track_and_update_status`, `test_invalid_status_rejected` | Pass |
| Block access to another student's records | `test_applications::test_students_cannot_touch_each_others_records` | Pass |

### Administrator
| Required test case | Automated test | Result |
|---|---|---|
| Administrator login | `test_admin::test_admin_login_lands_on_admin_dashboard` | Pass |
| Publish opportunities | `test_admin::test_publish_deactivate_delete_lifecycle` | Pass |
| Edit opportunities | `test_admin::test_edit_listing` | Pass |
| Deactivate opportunities | `test_admin::test_publish_deactivate_delete_lifecycle` | Pass |
| Reject unauthorised student access | `test_admin::test_students_get_403_on_admin_pages`, `test_students_cannot_post_admin_actions` | Pass |

### Additional behaviour covered
- Role cannot be chosen at sign-up or changed through the account form (`test_cannot_register_as_admin`, `test_security::test_role_cannot_be_changed_through_account_form`).
- Admin accounts can only be created from the command line (`test_create_admin_cli`, `test_promote_admin_cli`).
- Dangerous application URLs such as `javascript:` are rejected (`test_dangerous_urls_rejected`).
- HTML in listings, names and notes is escaped (`test_html_in_listing_is_escaped`, `test_stored_xss_is_escaped_everywhere`).
- Tracker and details pages state that the app does not submit applications (`test_tracker_does_not_claim_to_submit`).
- Database rules: unique emails, unique bookmarks and tracker entries, check constraints, foreign keys, cascade deletes (`test_database.py`).
- Deactivated or deleted listings disappear for the public but are handled cleanly in students' lists (`test_integration`).
- Expired listings are marked closed and excluded from upcoming deadlines (`test_integration`).

## 5. Security test summary (`test_security.py`)
| Area | What is tested |
|---|---|
| SQL injection | Nine hostile payloads sent to search, filters, login, registration, admin form and tracker fields; tables stay intact |
| XSS | Script and image-handler payloads in names and titles come back escaped |
| CSRF | A POST without a token is rejected (`test_auth::test_csrf_blocks_forged_posts`) |
| Sessions | HttpOnly and SameSite cookie flags; session reset on login |
| Brute force | Sixth attempt blocked even with the right password; other IPs unaffected; window expiry; IP-wide cap |
| Request size | Bodies over 1 MB return 413 |
| Production config | Weak or placeholder secret refuses to start; secure cookies and HSTS enabled |
| Open redirects | `//evil.com`, full URLs and backslash tricks ignored (`test_auth`) |

## 6. Automated accessibility checks
Every public, student and admin page is checked for: `lang` attribute, viewport meta tag, exactly one `h1`, unique element ids, a label or `aria-label` on every form field, an accessible name on every button, no images without alt text, and safe `target="_blank"` links.

## 7. What has NOT been tested yet
Be honest about these in your seminar:
- **Real browsers and devices:** layout at phone, tablet and desktop widths, Safari and iPhone behaviour, Android Chrome. Use `manual_test_checklist.md`.
- **Screen readers and colour contrast tools** (Lighthouse or axe).
- **Load and performance** testing.
- **Penetration testing** by an independent party.
- **A real AWS deployment** (Beanstalk, RDS, load balancer, HTTPS, CloudWatch). Everything up to that point is tested locally.
- **Email and file upload** (features not built yet).

## 8. Manual test results log
Copy results from `manual_test_checklist.md` here once done.

| Date | Browser / device | Width | Pages checked | Issues found | Fixed? |
|---|---|---|---|---|---|
| | | | | | |

## 9. Defects found and fixed during development
| Phase | Defect | Fix |
|---|---|---|
| 1 | pytest could not import `app` | Added `pytest.ini` with `pythonpath = .` |
| 2 | Search test failed because common words appeared in the footer and dropdown | Tests now assert on unique listing titles |
| 3 | Test database lost its tables because each connection to `:memory:` is separate | Tests use a temporary database file |
| 5 | Muted text colour had weak contrast | Darkened the colour (`--muted`) |
| 5 | Expired listings still looked open | Added "Closed" and "expired" markers and excluded them from upcoming deadlines |
| 5 | One test expected wording the page did not use | Test updated to match the page |
| 7 | A null byte (`\x00`) in any input crashed PostgreSQL with a 500 error (SQLite accepted it), found only by running the suite on PostgreSQL | Requests containing null bytes are rejected with 400 in `security.py`; tests accept 400 for that payload |
