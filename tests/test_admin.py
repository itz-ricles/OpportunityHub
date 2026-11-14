import pytest

import queries
from test_opportunities import NEW

ADMIN_GETS = ["/admin", "/admin/students", "/admin/opportunities/new", "/admin/opportunities/1/edit"]
ADMIN_POSTS = ["/admin/opportunities/new", "/admin/opportunities/1/edit", "/admin/opportunities/1/publish",
               "/admin/opportunities/1/deactivate", "/admin/opportunities/1/delete"]


def test_admin_login_lands_on_admin_dashboard(app, make_user, login):
    make_user("boss@example.com", "Kojo Boss", "admin")
    res = login(app.test_client(), "boss@example.com")
    assert res.headers["Location"].endswith("/admin")


@pytest.mark.parametrize("path", ADMIN_GETS)
def test_students_get_403_on_admin_pages(student, path):
    assert student.get(path).status_code == 403


@pytest.mark.parametrize("path", ADMIN_POSTS)
def test_students_cannot_post_admin_actions(student, app, path):
    assert student.post(path, data=NEW).status_code == 403
    with app.app_context():
        assert queries.get_opportunity(1) is not None and len(queries.list_opportunities()) == 7


@pytest.mark.parametrize("path", ADMIN_GETS)
def test_anonymous_redirected_from_admin(client, path):
    assert client.get(path).status_code == 302


def test_admin_dashboard_stats_and_listing(admin, student_factory=None):
    page = admin.get("/admin").data
    assert b"Active opportunities" in page and b"Demo Cloud Computing Fundamentals" in page
    assert b"Tracker activity" in page


def test_admin_sees_students(admin, make_user):
    make_user("ama@example.com", "Ama Mensah")
    page = admin.get("/admin/students").data
    assert b"Ama Mensah" in page and b"Kojo Boss" not in page


def test_edit_listing(admin, client):
    assert b"Demo Undergraduate Excellence" in admin.get("/admin/opportunities/1/edit").data
    res = admin.post("/admin/opportunities/1/edit", data={**NEW, "title": "Renamed Scholarship", "action": "save"})
    assert res.status_code == 302
    assert b"Renamed Scholarship" in client.get("/opportunities/1").data


def test_publish_deactivate_delete_lifecycle(admin, client):
    assert admin.post("/admin/opportunities/1/deactivate").status_code == 302
    assert client.get("/opportunities/1").status_code == 404
    assert admin.post("/admin/opportunities/1/publish").status_code == 302
    assert client.get("/opportunities/1").status_code == 200
    assert admin.post("/admin/opportunities/1/delete").status_code == 302
    assert client.get("/opportunities/1").status_code == 404
    assert admin.post("/admin/opportunities/1/delete").status_code == 404
