"""Single source of truth for fixed values. database/schema.sql CHECK constraints must match these."""

CATEGORIES = [
    ("Scholarships", "Undergraduate, postgraduate and research funding."),
    ("Internships", "Local, remote and international work experience."),
    ("Online Courses", "Free and paid courses and certifications."),
    ("Competitions", "Hackathons, innovation and research challenges."),
]
CATEGORY_NAMES = [name for name, _ in CATEGORIES]

SCOPES = ("Local", "International")
APPLICATION_STATUSES = ("Planning", "Applied", "Interview", "Rejected", "Successful")
OPPORTUNITY_STATUSES = ("draft", "published", "inactive")
ROLES = ("student", "admin")
