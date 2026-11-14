"""Automated accessibility checks on rendered HTML. (Real screen-reader / contrast testing is still manual.)"""
from html.parser import HTMLParser

import pytest


class Audit(HTMLParser):
    def __init__(self):
        super().__init__()
        self.lang = self.viewport = None
        self.ids, self.label_for, self.fields, self.buttons = [], set(), [], []
        self.h1 = 0
        self.problems = []
        self._btn = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = a.get("lang")
        if tag == "meta" and a.get("name") == "viewport":
            self.viewport = a.get("content")
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "label" and "for" in a:
            self.label_for.add(a["for"])
        if tag == "h1":
            self.h1 += 1
        if tag in ("input", "select", "textarea") and a.get("type") not in ("hidden", "submit"):
            self.fields.append(a)
        if tag == "img" and "alt" not in a:
            self.problems.append("img without alt")
        if tag == "a" and a.get("target") == "_blank" and "noopener" not in a.get("rel", ""):
            self.problems.append("target=_blank without rel=noopener")
        if tag == "button":
            self._btn = [a, ""]

    def handle_data(self, data):
        if self._btn is not None:
            self._btn[1] += data

    def handle_endtag(self, tag):
        if tag == "button" and self._btn:
            self.buttons.append(self._btn)
            self._btn = None


def audit(html):
    p = Audit()
    p.feed(html.decode())
    assert p.lang == "en", "missing lang"
    assert p.viewport and "width=device-width" in p.viewport
    assert p.h1 == 1, f"expected one h1, found {p.h1}"
    assert len(p.ids) == len(set(p.ids)), "duplicate ids"
    for f in p.fields:
        assert f.get("id") in p.label_for or f.get("aria-label"), f"field without label: {f}"
    for attrs, text in p.buttons:
        assert text.strip() or attrs.get("aria-label"), "button without accessible name"
    assert not p.problems, p.problems


PUBLIC = ["/", "/login", "/register", "/opportunities", "/opportunities/1", "/opportunities?q=zzzz"]
STUDENT = ["/dashboard", "/saved", "/applications", "/account", "/opportunities/1"]
ADMIN = ["/admin", "/admin/students", "/admin/opportunities/new", "/admin/opportunities/1/edit"]


@pytest.mark.parametrize("path", PUBLIC)
def test_public_pages(client, path):
    audit(client.get(path).data)


@pytest.mark.parametrize("path", STUDENT)
def test_student_pages(student, path):
    student.post("/opportunities/1/save")
    student.post("/opportunities/1/track")
    audit(student.get(path).data)


@pytest.mark.parametrize("path", ADMIN)
def test_admin_pages(admin, path):
    audit(admin.get(path).data)


def test_error_page(client):
    audit(client.get("/nope").data)
