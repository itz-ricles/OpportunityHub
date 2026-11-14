import queries

NEW = {"title": "Test Grant", "category": "Scholarships", "organisation": "Test Org (fictional)",
       "location": "Ghana", "geographical_scope": "Local", "description": "Desc", "eligibility": "Elig",
       "funding_information": "", "application_url": "https://example.com/grant", "deadline": "2027-05-01",
       "action": "publish"}


def test_admin_created_listing_appears_publicly(admin, client):
    assert admin.post("/admin/opportunities/new", data=NEW).status_code == 302
    assert b"Test Grant" in client.get("/opportunities").data


def test_draft_is_not_public(admin, client):
    admin.post("/admin/opportunities/new", data={**NEW, "action": "draft"})
    assert b"Test Grant" not in client.get("/opportunities").data


def test_listing_page_shows_real_records(client):
    page = client.get("/opportunities").data
    assert b"Demo Undergraduate Excellence Scholarship" in page and b"7 results" in page


def test_search_and_filters(client):
    assert b"Demo Cloud Computing Fundamentals" in client.get("/opportunities?q=cloud").data
    res = client.get("/opportunities?category=Competitions").data
    assert b"Demo Student Innovation Challenge" in res and b"Demo Software Engineering Internship" not in res
    assert b"Demo Remote Data Analysis Internship" not in client.get("/opportunities?scope=Local").data
    assert b"No opportunities match" in client.get("/opportunities?q=zzzz").data


def test_details_page_and_safe_external_link(client):
    page = client.get("/opportunities/1").data
    assert b"Eligibility" in page and b"https://example.com/demo-scholarship" in page
    assert b'target="_blank" rel="noopener noreferrer"' in page
    assert b"We do not award scholarships" in page


def test_dangerous_urls_rejected(admin, ctx):
    res = admin.post("/admin/opportunities/new", data={**NEW, "application_url": "javascript:alert(1)"})
    assert res.status_code == 400 and b"http://" in res.data
    assert all(r["title"] != "Test Grant" for r in queries.list_opportunities(include_all=True))


def test_invalid_listing_fields_rejected(admin):
    for bad in ({"category": "Bogus"}, {"geographical_scope": "Mars"}, {"deadline": "tomorrow"},
                {"deadline": "2027-13-45"}, {"title": ""}):
        assert admin.post("/admin/opportunities/new", data={**NEW, **bad}).status_code == 400


def test_html_in_listing_is_escaped(admin, client):
    admin.post("/admin/opportunities/new", data={**NEW, "title": "<script>alert(1)</script>"})
    page = client.get("/opportunities").data
    assert b"<script>alert(1)</script>" not in page and b"&lt;script&gt;" in page
