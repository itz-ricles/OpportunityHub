"""Server-side validation. Never trust the browser: HTML attributes are only a convenience."""
import re
from datetime import date
from urllib.parse import urlparse

from constants import CATEGORY_NAMES, SCOPES

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MIN_PASSWORD = 8


def validate_password(password, confirm):
    errors = {}
    if not password:
        errors["password"] = "Enter a password."
    elif len(password) < MIN_PASSWORD:
        errors["password"] = f"Password must be at least {MIN_PASSWORD} characters."
    elif len(password) > 128:
        errors["password"] = "Password must be 128 characters or fewer."
    if password and confirm != password:
        errors["confirm_password"] = "Passwords do not match."
    return errors


def validate_name(name):
    if not name:
        return "Enter your full name."
    if len(name) > 100:
        return "Name must be 100 characters or fewer."
    return None


def validate_registration(form):
    data = {
        "full_name": form.get("full_name", "").strip(),
        "email": form.get("email", "").strip().lower(),
        "password": form.get("password", ""),
    }
    errors = {}
    name_error = validate_name(data["full_name"])
    if name_error:
        errors["full_name"] = name_error
    if not data["email"]:
        errors["email"] = "Enter your email address."
    elif len(data["email"]) > 254 or not EMAIL_RE.match(data["email"]):
        errors["email"] = "Enter a valid email address."
    errors.update(validate_password(data["password"], form.get("confirm_password", "")))
    return data, errors


def _is_web_url(value):
    parts = urlparse(value)
    return parts.scheme in ("http", "https") and bool(parts.netloc)


def validate_opportunity(form):
    """Returns (cleaned_data, errors). Only http(s) links are allowed, which blocks javascript: URLs."""
    get = lambda k: form.get(k, "").strip()
    data = {k: get(k) for k in (
        "title", "category", "organisation", "location", "geographical_scope",
        "description", "eligibility", "funding_information", "application_url", "deadline")}
    errors = {}
    limits = {"title": 200, "organisation": 200, "location": 200, "description": 5000,
              "eligibility": 5000, "funding_information": 2000, "application_url": 2000}
    labels = {"title": "title", "organisation": "organisation", "location": "location",
              "description": "description", "eligibility": "eligibility", "application_url": "application URL"}
    for key, label in labels.items():
        if not data[key]:
            errors[key] = f"Enter the {label}."
    for key, limit in limits.items():
        if len(data[key]) > limit:
            errors[key] = f"The {key.replace('_', ' ')} must be {limit} characters or fewer."
    if data["category"] not in CATEGORY_NAMES:
        errors["category"] = "Choose a category."
    if data["geographical_scope"] not in SCOPES:
        errors["geographical_scope"] = "Choose Local or International."
    if data["application_url"] and "application_url" not in errors and not _is_web_url(data["application_url"]):
        errors["application_url"] = "The application URL must start with http:// or https://."
    try:
        if not DATE_RE.match(data["deadline"]):
            raise ValueError
        date.fromisoformat(data["deadline"])
    except ValueError:
        errors["deadline"] = "Enter the deadline as a valid date."
    data["funding_information"] = data["funding_information"] or None
    return data, errors
