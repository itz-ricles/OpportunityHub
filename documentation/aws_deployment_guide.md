# OpportunityHub: AWS Deployment Guide (Phase 7)

> **Status: prepared, not yet deployed.** The application has been tested locally on SQLite and on a real PostgreSQL 16 server, and runs under gunicorn in production mode. The AWS console steps below follow AWS's documentation but **have not been executed on a real AWS account**, and AWS screens change often. Treat this as a plan to follow carefully, and check each step against the current AWS docs.

## 0. Gate: do not deploy until all of these are true
- [ ] Manual checklist (`manual_test_checklist.md`) completed on phone, tablet and desktop, and issues fixed
- [ ] `pytest` passes, and also passes against PostgreSQL (section 9)
- [ ] `bandit` and `pip-audit` are clean
- [ ] You generated a **new** `SECRET_KEY` for production (never reuse your local one)
- [ ] You decided what to do with demo data (the 7 seeded listings are fictional and labelled so)

## 1. What Phase 7 changed in the code
| Change | Why AWS needs it |
|---|---|
| `DATABASE_URL` support (PostgreSQL) in `db.py` and `queries.py` | SQLite lives on the server's disk and is wiped when the server is replaced; RDS is the managed database |
| `scripts/migrate_sqlite_to_postgres.py` | Moves existing data to RDS and keeps ids and links intact |
| `wsgi.py`, `Procfile`, `gunicorn` | Production web server; Elastic Beanstalk's Python platform uses Gunicorn and reads a `Procfile` |
| `FLASK_ENV` now defaults to **production** | Forgetting the variable can no longer turn on debug mode on a public server |
| `FORCE_HTTPS`, secure cookies, HSTS | Protects logins; cookies marked Secure only travel over HTTPS |
| `TRUSTED_PROXY_COUNT` (ProxyFix) | Behind a load balancer every request looks like it comes from the balancer; this restores the real visitor IP so rate limiting works and cannot be spoofed |
| `/health` endpoint | Load balancer health checks; returns 200 only if the database answers |
| Logging to stderr (failed logins, admin actions) | CloudWatch collects instance logs |
| Null-byte rejection | Found by running the tests on PostgreSQL: it crashed with a 500 error, SQLite did not |
| `.ebignore`, `deploy/` (systemd + nginx samples), `.env.example` | Packaging and the EC2 option |

## 2. Target architecture
```mermaid
flowchart LR
    U[Students and admins] -->|HTTPS| LB[Load balancer with ACM certificate]
    LB --> EB["Elastic Beanstalk: nginx + gunicorn + Flask"]
    EB -->|port 5432, private| RDS[("RDS PostgreSQL")]
    EB -.->|future uploads| S3[("S3 bucket, private")]
    EB -->|logs| CW[CloudWatch Logs and alarms]
    IAM[IAM instance role] -.-> EB
```

## 3. Before you touch AWS: safety and cost
1. **Secure the account:** turn on MFA for the root user, create a normal IAM or Identity Center user for daily work, and stop using root.
2. **Set a budget alert first** (AWS Budgets) with email notifications at a low amount.
3. **Know your free-tier rules.** AWS changed them in July 2025. Reports from 2026 say accounts created on or after 15 July 2025 get credits (around $100 to $200) on a Free plan that lasts up to 6 months or until credits run out, and then the account closes unless upgraded, while older accounts keep the 12-month model. Read your own **Billing and Free Tier** page instead of trusting blog posts, because this has changed recently.
4. **Things that quietly cost money:** load balancers, NAT gateways, idle RDS instances, unattached Elastic IPs, and snapshots. Follow the teardown list (section 12) right after your seminar.
5. Never commit `.env`, passwords or AWS keys to GitHub.

## 4. Environment variables
Set these in the Elastic Beanstalk console (Configuration, Updates, monitoring and logging, Environment properties) or in `/etc/opportunityhub.env` on EC2.

| Variable | Production value |
|---|---|
| `FLASK_ENV` | `production` |
| `SECRET_KEY` | 64 random hex characters: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL` | `postgresql://USER:PASSWORD@RDS-ENDPOINT:5432/opportunityhub` (URL-encode special characters in the password, e.g. `@` becomes `%40`) |
| `FORCE_HTTPS` | `true` (leave as is). `false` only for a short HTTP-only demo with no real passwords |
| `TRUSTED_PROXY_COUNT` | See section 7. Wrong values break the rate limiter |
| `LOG_LEVEL` | `INFO` |

The app refuses to start in production if `SECRET_KEY` is missing, shorter than 32 characters, or starts with `change-me`.

## 5. Step 1: PostgreSQL on Amazon RDS
1. RDS, Create database, engine **PostgreSQL** (version 16 is what the tests ran on), a dev/test or free-tier template, **single-AZ**, the smallest burstable instance class your account offers, 20 GB storage.
2. Set a database name `opportunityhub`, a master username, and a strong generated password. Store the password in a password manager.
3. **Public access: No.** Put it in the same VPC as your application.
4. Security group: allow inbound **TCP 5432 only from your application's security group**, not from the internet.
5. Keep automated backups on (default retention is fine).
6. Copy the endpoint host name for `DATABASE_URL`.

Optional hardening: create a separate app user instead of using the master user:
```sql
CREATE USER ohub_app WITH PASSWORD '...';
GRANT CONNECT ON DATABASE opportunityhub TO ohub_app;
GRANT USAGE, CREATE ON SCHEMA public TO ohub_app;
```

## 6A. Path A (recommended): Elastic Beanstalk
Beanstalk runs Python behind nginx with Gunicorn as the default WSGI server, installs from the `requirements.txt` in your upload, and starts the command in your `Procfile`.

1. **Build the upload.** The zip must have `Procfile`, `requirements.txt` and `wsgi.py` at its top level (zip the folder's contents, not the folder itself). Leave out `.env`, `venv`, `*.db`, `tests`, `documentation`. On macOS/Linux:
   ```
   zip -r ../opportunityhub-eb.zip . -x ".env" "venv/*" "*.db" "tests/*" "documentation/*" ".git/*" "__pycache__/*"
   ```
   (If you use the EB CLI, `.ebignore` already does this.)
2. **Create the environment:** Elastic Beanstalk, Create application, Web server environment, Python platform (pick the newest Python branch it lists; development used 3.12), upload the zip.
3. **Single instance or load balanced?** Single instance is cheapest but HTTPS is harder to set up. A **load-balanced** environment lets you attach an HTTPS certificate (step 6A.5). For a real demo with logins, choose load balanced.
4. **Environment properties:** add the variables from section 4.
5. **HTTPS:** you need a domain name you control. Request a certificate in AWS Certificate Manager (DNS validation), add an HTTPS (443) listener to the load balancer using it, and redirect HTTP to HTTPS. Point your domain at the load balancer.
6. **Health check:** set the load balancer or process health check path to `/health`.
7. **Network:** allow the environment's instance security group to reach RDS on 5432 (step 5.4).
8. **Create the tables and your admin.** Open a shell on the instance (EB CLI `eb ssh`, or Session Manager), make sure the environment variables are loaded in that shell (the Beanstalk docs explain how for your platform version), then from the application folder:
   ```
   flask --app wsgi init-db
   flask --app wsgi seed-db            # optional demo listings (fictional)
   flask --app wsgi create-admin
   ```
   Optional, **untested** idea for automating the table creation on each deploy: an `.ebextensions` config with a `container_commands` entry that runs `flask --app wsgi init-db` on the leader instance. `init-db` is safe to repeat.
9. Visit `/health` first, then the home page.

## 6B. Path B: a single EC2 server
Use this if you want to learn Linux server basics. More manual work, fewer AWS services.
1. Launch a small Linux instance, security group open on 80 and 443 (and 22 only from your IP).
2. Install Python, nginx and git; copy the project to `/opt/opportunityhub`; create a virtualenv and `pip install -r requirements.txt`.
3. Create `/etc/opportunityhub.env` (permissions `600`) with the section 4 variables. Use `TRUSTED_PROXY_COUNT=1` (nginx is the only proxy).
4. Copy `deploy/opportunityhub.service` to `/etc/systemd/system/`, then `systemctl enable --now opportunityhub`.
5. Copy `deploy/nginx.conf` into nginx's configuration, set your domain, reload nginx, then get a free certificate with certbot.
6. Run the `init-db` and `create-admin` commands with the same environment file loaded.

## 7. `TRUSTED_PROXY_COUNT`: get this right
It tells the app how many proxies in front of it to trust for the visitor's real IP.
| Setup | Value |
|---|---|
| Local, or gunicorn directly exposed | `0` |
| EC2 with only nginx in front | `1` |
| Beanstalk behind a load balancer (nginx on the instance plus the balancer) | probably `2`, but **verify**: log in with a wrong password from your phone, check the "Failed login attempt ip=..." line in the logs, and confirm it shows your public IP, not a private `10.x` or `172.x` address |

Too low: everyone shares the balancer's IP, so five failed logins by one person lock out everybody. Too high: attackers can fake their IP with a forged header.

## 8. Moving existing local data to RDS (optional)
Only if you have real accounts or listings worth keeping. From a machine that can reach the database (for example the EB instance, since RDS is private):
```
python scripts/migrate_sqlite_to_postgres.py --sqlite database/opportunityhub.db --postgres "postgresql://USER:PASSWORD@HOST:5432/opportunityhub"
```
It refuses to run if the target already has data, keeps all ids, verifies row counts before committing, and fixes the id counters. It was tested locally: users, listings, bookmarks and tracker notes survived, logins still worked, and new rows got the next ids.

## 9. Testing against PostgreSQL yourself
```
# with a local PostgreSQL and an empty database whose name contains "test"
TEST_DATABASE_URL="postgresql://user:password@localhost/ohub_test" pytest
```
Each test wipes that database, so the suite refuses to run unless its name contains `test`. On Windows PowerShell set the variable first: `$env:TEST_DATABASE_URL="..."`.

## 10. Monitoring with CloudWatch
- Turn on log streaming to CloudWatch Logs for the environment (Beanstalk monitoring and logging settings).
- What the app logs: failed logins (`Failed login attempt ip=...`), blocked logins (`Login blocked`), successful logins by user id, admin actions (`admin_id=... action=... opportunity_id=...`), unhandled errors with a traceback, and health-check failures. Passwords and email addresses are never logged.
- Suggested alarms: load balancer 5xx errors, unhealthy host count, RDS CPU, RDS free storage, plus the budget alert.

## 11. IAM, secrets and future S3
- Give the application **no AWS access keys**. It runs with the instance's IAM role, and today it needs nothing beyond what Beanstalk attaches by default, because the database is reached over the network with its password.
- Environment properties are visible to anyone who can open the Beanstalk console. A stronger option for later is AWS Secrets Manager or Systems Manager Parameter Store.
- **S3 is not used yet** because the app has no uploads. When you add images or files: create a private bucket with "Block all public access" on, give the instance role permission for only that bucket, store only the object key in the database, and serve files with short-lived presigned URLs.

## 12. Post-deploy verification and teardown
**Verify:**
- [ ] `/health` returns `{"status":"ok"}`
- [ ] The site loads over **https** and http redirects to https
- [ ] DevTools, Application, Cookies: the session cookie shows HttpOnly, Secure and SameSite=Lax
- [ ] Register a student, log in, save, track, log out
- [ ] A student opening `/admin` gets "Access denied"
- [ ] Admin can add, edit, deactivate and delete a listing
- [ ] Six wrong passwords in a row are blocked, and the log shows your real IP
- [ ] Run the manual checklist again on the live URL, on your phone

**Teardown after the seminar:** terminate the Beanstalk environment (this removes its load balancer and instances), delete the RDS instance and any snapshots you do not need, delete any S3 buckets, release unused Elastic IPs, delete unused certificates only if you want to, and check the Billing page again the next day.

## 13. Known limitations on AWS
- Login rate limiting is counted per gunicorn worker (2 per instance), so the real limit is a few times higher than configured, and more with several instances. A shared store (Redis via ElastiCache) with Flask-Limiter is the fix.
- Sessions are signed cookies, so extra instances work as long as every instance has the same `SECRET_KEY`.
- A new database connection is opened per request. This is fine for seminar-scale traffic; add connection pooling before heavy use.
- Dates are stored as ISO text on both databases to keep behaviour identical. Moving to native `DATE` columns later is a deliberate refactor.
- No email verification or password reset, no uploads, and no backup restore drill yet.

## 14. Suggested seminar demo (about 10 minutes)
1. Show the live URL and the padlock, then the landing page on your phone.
2. Register a student, search and filter, open a listing, follow the official-site link.
3. Save it, track it, change its status, show the dashboard.
4. Log in as admin in a private window: add a listing, publish it, see it appear for the student.
5. Show a student getting "Access denied" on `/admin`.
6. Show CloudWatch logs of the failed login and admin action, then the architecture diagram.
