"""End-to-end journeys: several features working together, the way real users hit them."""
import queries

LISTING = {"title": "Journey Grant", "category": "Scholarships", "organisation": "Journey Org (fictional)",
           "location": "Ghana", "geographical_scope": "Local", "description": "Desc", "eligibility": "Elig",
           "funding_information": "Demo", "application_url": "https://example.com/j", "deadline": "2027-09-01",
           "action": "publish"}


def test_full_student_journey(client, app):
    # sign up and log in
    assert client.post("/register", data={"full_name": "Ama Mensah", "email": "ama@example.com",
                                          "password": "password123", "confirm_password": "password123"}).status_code == 302
    assert client.post("/login", data={"email": "ama@example.com", "password": "password123"}).status_code == 302
    # discover
    assert b"Demo Cloud Computing Fundamentals" in client.get("/opportunities?q=cloud&category=Online+Courses").data
    assert b"Go to official site" in client.get("/opportunities/6").data
    # save + track + progress
    client.post("/opportunities/6/save")
    client.post("/opportunities/6/track")
    client.post("/applications/6/status", data={"application_status": "Applied", "notes": "Sent on the portal"})
    dash = client.get("/dashboard").data
    assert b"Welcome back, Ama" in dash and b"Applied" in dash
    # clean up and leave
    client.post("/opportunities/6/unsave", data={"next": "/saved"})
    assert b"not saved anything" in client.get("/saved").data
    client.post("/logout")
    assert client.get("/applications").status_code == 302
    with app.app_context():
        assert queries.get_stats()["students"] == 1


def test_admin_changes_ripple_through_to_students(admin, student, client, app):
    admin.post("/admin/opportunities/new", data=LISTING)
    with app.app_context():
        new_id = [r for r in queries.list_opportunities() if r["title"] == "Journey Grant"][0]["id"]
    assert b"Journey Grant" in student.get("/opportunities").data
    student.post(f"/opportunities/{new_id}/save")
    student.post(f"/opportunities/{new_id}/track")
    stats = admin.get("/admin").data
    assert b"Journey Grant" in stats

    # deactivated: gone from public pages, kept in the student's own lists and clearly marked
    admin.post(f"/admin/opportunities/{new_id}/deactivate")
    assert client.get(f"/opportunities/{new_id}").status_code == 404
    assert b"No longer listed" in student.get("/saved").data
    assert b"no longer listed" in student.get("/applications").data
    # the student can still update their own tracker entry
    assert student.post(f"/applications/{new_id}/status", data={"application_status": "Rejected"}).status_code == 302

    # deleted: everything referencing it disappears
    admin.post(f"/admin/opportunities/{new_id}/delete")
    assert b"Journey Grant" not in student.get("/saved").data
    assert b"Journey Grant" not in student.get("/applications").data


def test_expired_listing_is_flagged_closed(admin, client):
    admin.post("/admin/opportunities/new", data={**LISTING, "title": "Old Grant", "deadline": "2020-01-01"})
    assert b"Closed" in client.get("/opportunities").data
    assert b"This deadline has passed" in client.get("/opportunities/8").data
    assert b"expired" in admin.get("/admin").data


def test_closed_listings_dont_count_as_upcoming(student, admin, app):
    admin.post("/admin/opportunities/new", data={**LISTING, "title": "Old Grant", "deadline": "2020-01-01"})
    student.post("/opportunities/8/save")
    assert b"Old Grant" not in student.get("/dashboard").data.split(b"Upcoming deadlines")[1]
