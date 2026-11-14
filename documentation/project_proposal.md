# OpportunityHub: Project Proposal

**Project type:** Full-stack web application (EdTech)  
**Target users:** University and tertiary students in Ghana  
**Developer:** Solo student project  
**Author:** [add your name, index number and course here]

## 1. Problem statement
Students often struggle to find reliable information about scholarships, internships, exchange programmes, online courses and competitions. The information is spread across many websites, social media pages and institutional announcements, so students miss deadlines or never hear about opportunities they qualify for.

## 2. Aim
Build a single platform where students can discover opportunities, check eligibility, save the ones they care about and organise their own application progress.

## 3. Objectives
1. Provide a centralised platform for discovering educational and professional opportunities.
2. Improve access to local and international scholarships.
3. Help students find internships and professional development programmes.
4. Offer a searchable database of opportunities.
5. Let students save opportunities for later.
6. Help students organise and monitor their applications.
7. Give administrators tools to manage listings.
8. Reduce the effort of finding relevant opportunities.
9. Create a foundation for future intelligent recommendations.

## 4. Scope
**In scope (current version):** student and administrator accounts, four categories (Scholarships, Internships, Online Courses, Competitions), search, filtering and sorting, details pages, bookmarks, application tracker, student dashboard, admin dashboard and listing management, automated tests, documentation.

**Out of scope for now:** submitting applications on behalf of students, payments, messaging, email notifications, AI recommendations, mobile apps, cloud deployment (planned afterwards).

## 5. Users
| Role | Needs |
|---|---|
| Student | Find relevant opportunities quickly, see eligibility and deadlines, keep track of progress |
| Administrator | Add accurate listings, hide expired ones, monitor usage |

## 6. Technology
Python and Flask (backend), Jinja2, HTML5, CSS3 and JavaScript (frontend), SQLite (local database, designed to move to PostgreSQL), Git and GitHub (version control), Visual Studio Code. Future hosting on AWS (EC2 or Elastic Beanstalk, RDS, S3, IAM, CloudWatch).

## 7. Method
Incremental development in phases, testing at each step:
1. Project initialisation
2. Frontend and responsive layout
3. Database design and demo data
4. Backend: authentication, roles, bookmarks, tracker, admin tools
5. Integration, security review and testing
6. Documentation
7. AWS preparation and deployment

## 8. Ethical and legal considerations
- The platform lists opportunities and links to official provider websites; it does not award scholarships or guarantee acceptance, and says so in the interface.
- Demo listings are clearly fictional. Real listings must be copied from official provider sources, and deadlines, eligibility or funding must never be invented.
- Student data is limited to name, email and a hashed password. Passwords are never stored in plain text.

## 9. Risks and mitigations
| Risk | Mitigation |
|---|---|
| Out-of-date or wrong listings | Admin-only publishing, status field to hide expired items, links to official sources, "Closed" markers |
| Account or data attacks | Password hashing, CSRF protection, role checks, rate limiting, automated security tests |
| Scope creep for a solo developer | Phased plan; advanced features stay optional until the core works |
| Hard to maintain | Small codebase, one place for SQL, clear documentation, automated tests |

## 10. Success criteria
- A student can register, find an opportunity, save it, track it and update its status.
- An administrator can publish, edit, deactivate and delete listings; students can never reach admin functions.
- The automated test suite passes, and the manual checklist is completed on phones, tablets and desktops.
- The application can be demonstrated at a university seminar and prepared for AWS deployment.

## 11. Future work
AI-powered recommendations, email notifications, student profiles, advanced filters, analytics, expansion to other African countries.
