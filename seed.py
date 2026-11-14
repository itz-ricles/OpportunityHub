"""Demonstration data. Every organisation is FICTIONAL and every detail is a placeholder.
Do not present any of this as a real scholarship, deadline or funding offer."""
import queries
from db import get_db

SEED_OPPORTUNITIES = [
    dict(title="Demo Undergraduate Excellence Scholarship", category="Scholarships",
         organisation="Demo Foundation Ghana (fictional)", location="Ghana", geographical_scope="Local",
         deadline="2026-12-15", application_url="https://example.com/demo-scholarship",
         description="Demonstration listing for a Ghanaian undergraduate scholarship.",
         eligibility="Demo eligibility: enrolled in a Ghanaian university. Not real criteria.",
         funding_information="Demo funding: partial tuition support. Not a real amount."),
    dict(title="Demo International Postgraduate Scholarship", category="Scholarships",
         organisation="Example Global Trust (fictional)", location="United Kingdom", geographical_scope="International",
         deadline="2027-01-20", application_url="https://example.com/demo-postgrad",
         description="Demonstration listing for a fully funded international master's programme.",
         eligibility="Demo eligibility: first-class or upper second-class degree. Not real criteria.",
         funding_information="Demo funding: full tuition and stipend. Not a real offer."),
    dict(title="Demo Software Engineering Internship", category="Internships",
         organisation="Sample Tech Accra (fictional)", location="Accra, Ghana", geographical_scope="Local",
         deadline="2026-12-01", application_url="https://example.com/demo-internship",
         description="Demonstration listing for a local technology internship.",
         eligibility="Demo eligibility: IT or CS student, level 300 or above.",
         funding_information="Demo: monthly stipend."),
    dict(title="Demo Remote Data Analysis Internship", category="Internships",
         organisation="Sample Analytics Ltd (fictional)", location="Remote", geographical_scope="International",
         deadline="2027-02-10", application_url="https://example.com/demo-remote",
         description="Demonstration listing for an international remote internship.",
         eligibility="Demo eligibility: basic Python and statistics.",
         funding_information="Demo: unpaid, certificate provided."),
    dict(title="Demo Free Python Programming Course", category="Online Courses",
         organisation="Example Learning (fictional)", location="Online", geographical_scope="International",
         deadline="2027-03-30", application_url="https://example.com/demo-python",
         description="Demonstration listing for a free online programming course.",
         eligibility="Demo eligibility: open to everyone.", funding_information="Free."),
    dict(title="Demo Cloud Computing Fundamentals", category="Online Courses",
         organisation="Example Cloud Academy (fictional)", location="Online", geographical_scope="International",
         deadline="2027-04-15", application_url="https://example.com/demo-cloud",
         description="Demonstration listing for an international cloud computing course.",
         eligibility="Demo eligibility: basic IT knowledge.", funding_information="Demo: paid course."),
    dict(title="Demo Student Innovation Challenge", category="Competitions",
         organisation="Sample Innovation Hub (fictional)", location="Kumasi, Ghana", geographical_scope="Local",
         deadline="2026-12-20", application_url="https://example.com/demo-challenge",
         description="Demonstration listing for a student innovation competition.",
         eligibility="Demo eligibility: teams of 2 to 4 university students.",
         funding_information="Demo: prize money. Not a real prize."),
]


def seed_opportunities():
    """Insert demo rows only if the table is empty. Returns how many were added."""
    if get_db().execute("SELECT COUNT(*) FROM opportunities").fetchone()[0] > 0:
        return 0
    for item in SEED_OPPORTUNITIES:
        queries.create_opportunity(item, status="published")
    return len(SEED_OPPORTUNITIES)
