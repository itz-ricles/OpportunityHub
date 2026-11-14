import queries


def uid(app, email="ama@example.com"):
    with app.app_context():
        return queries.get_user_by_email(email)["id"]


def counts(app, user_id):
    with app.app_context():
        return queries.count_saved(user_id), queries.count_applications(user_id)


def test_save_unsave_and_no_duplicates(student, app):
    u = uid(app)
    assert student.post("/opportunities/1/save").status_code == 302
    dup = student.post("/opportunities/1/save", follow_redirects=True)
    assert b"already saved" in dup.data and counts(app, u)[0] == 1
    assert b"Demo Undergraduate Excellence Scholarship" in student.get("/saved").data
    student.post("/opportunities/1/unsave")
    assert counts(app, u)[0] == 0


def test_saved_persists_across_sessions(student, app, login):
    student.post("/opportunities/2/save")
    again = app.test_client()
    login(again)
    assert b"Demo International Postgraduate" in again.get("/saved").data


def test_track_and_update_status(student, app):
    u = uid(app)
    student.post("/opportunities/3/track")
    assert b"already tracking" in student.post("/opportunities/3/track", follow_redirects=True).data
    assert counts(app, u)[1] == 1
    res = student.post("/applications/3/status", data={"application_status": "Interview", "notes": "Panel on Monday"})
    assert res.status_code == 302
    page = student.get("/applications").data
    assert b"Panel on Monday" in page and b"Demo Software Engineering Internship" in page
    with app.app_context():
        assert queries.get_application(u, 3)["application_status"] == "Interview"


def test_invalid_status_rejected(student, app):
    student.post("/opportunities/3/track")
    res = student.post("/applications/3/status", data={"application_status": "Hired"}, follow_redirects=True)
    assert b"valid status" in res.data
    with app.app_context():
        assert queries.get_application(uid(app), 3)["application_status"] == "Planning"


def test_students_cannot_touch_each_others_records(student, app, make_user, login):
    student.post("/opportunities/3/track")
    student.post("/opportunities/3/save")
    make_user("kwame@example.com", "Kwame Asare")
    other = app.test_client()
    login(other, "kwame@example.com")
    assert other.post("/applications/3/status", data={"application_status": "Successful"}).status_code == 404
    assert b"Demo Software Engineering Internship" not in other.get("/applications").data
    assert b"Demo Software Engineering Internship" not in other.get("/saved").data
    with app.app_context():
        assert queries.get_application(uid(app), 3)["application_status"] == "Planning"


def test_dashboard_shows_real_numbers(student):
    student.post("/opportunities/1/save")
    student.post("/opportunities/3/track")
    page = student.get("/dashboard").data
    assert b"Welcome back, Ama" in page and b"Demo Software Engineering Internship" in page


def test_tracker_does_not_claim_to_submit(student):
    assert b"does not submit applications" in student.get("/applications").data
    assert b"submit applications for you" in student.get("/opportunities/1").data


def test_anonymous_actions_redirect_to_login(client):
    for path in ("/opportunities/1/save", "/opportunities/1/track", "/applications/1/status"):
        res = client.post(path)
        assert res.status_code == 302 and "/login" in res.headers["Location"]


def test_cannot_save_unknown_listing(student):
    assert student.post("/opportunities/9999/save").status_code == 404
