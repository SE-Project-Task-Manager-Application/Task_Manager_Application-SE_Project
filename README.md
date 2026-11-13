# Task Manager Application

A Django web application for creating, organising, assigning, sharing and tracking tasks.
Roles: Team Member, Project Manager and Administrator.

## Requirements

- Python 3.12 or newer
- Docker Desktop (runs PostgreSQL and the MailHog test mail server)
- Git

## Quick start (local development)

From the repository root:

1. Create and activate a virtual environment:
   - Mac/Linux: `python3 -m venv .venv` then `source .venv/bin/activate`
   - Windows: `python -m venv .venv` then `.venv\Scripts\activate`
2. Install the dependencies:
   ```bash
   python -m pip install -r requirements.txt -r requirements-dev.txt
   ```
3. Create your private settings file:
   - Mac/Linux: `cp .env.example .env`
   - Windows: `copy .env.example .env`

   Then generate a Django secret key with
   `python -c "import secrets; print(secrets.token_urlsafe(50))"` and paste the result as the
   value of `DJANGO_SECRET_KEY` in `.env`. `.env` is ignored by Git. Never commit it or share
   your key.
4. Start PostgreSQL and MailHog:
   ```bash
   docker compose up -d
   ```
5. Create the database tables and the test data:
   ```bash
   python manage.py migrate
   python manage.py seed_test_data
   ```
6. Start the app:
   ```bash
   python manage.py runserver
   ```
   Open http://127.0.0.1:8000/ in your browser.

## Test accounts

`seed_test_data` creates these accounts, plus sample tasks in each status and sample labels
(Bug, Feature, Documentation, and an archived one, Legacy). It is safe to run twice and
refuses to run outside the dev/test settings.

| Role            | Email                |
|-----------------|----------------------|
| Team Member     | member@example.com   |
| Project Manager | pm@example.com       |
| Administrator   | admin@example.com    |

Password for all test accounts (test only): `SEPROG123`

## Services

- PostgreSQL 16 listens on 127.0.0.1:5432. Django reads `DB_NAME`, `DB_USER`, `DB_PASSWORD`,
  `DB_HOST` and `DB_PORT` from `.env`.
- MailHog receives e-mail on 127.0.0.1:1025. Read the captured messages in its inbox at
  http://127.0.0.1:8025/ (registration, password-reset, e-mail-change and assignment mails).
- Task reminders have a 24-hour lead time: they become eligible at `due_date - 24 hours`.
  Schedule `python manage.py send_due_reminders` once per minute. It queues reminders for
  open tasks due within the next 24 hours, then sends them on the first run at or after
  their scheduled time. If a task is created inside its 24-hour window, its reminder is
  queued on the next run. Reminders go to every assignee; when there are no assignees, the
  task owner receives the reminder.
  Each run claims at most 5 due rows (at most 25 seconds at the configured five-second SMTP
  timeout), skips rows locked by another runner, and stops after its first mail failure.
  More than 5 due reminders in a run can spill into later runs, so larger bursts may exceed
  the one-minute target.
  Failed sends retry on later runs, up to 120 failed attempts. At the once-per-minute
  schedule, that is up to two hours of retry time; after 120 failures the notification is
  marked terminally failed and is not automatically retried. A reminder is cancelled if
  its task is completed, deleted, rescheduled, or becomes overdue. The command is safe to
  repeat.

  To exercise a real MailHog outage, first create a task due within 24 hours, then stop
  MailHog and run the command. It should report a failed send without crashing and leave
  the notification pending. Restart MailHog and run the command again; it should deliver
  the email. Check the inbox at http://localhost:8025/.
- Stop the services: `docker compose down`.
- Stop them and wipe the database (deletes all data): `docker compose down -v`.
- If `docker compose up` says port 5432 is already in use, another PostgreSQL is running on
  your machine. Stop it, then start the services again.

## Running tests and lint

With the services running (the tests use the PostgreSQL container):

```bash
pytest
ruff check .
```

`pytest` uses `config.settings.test`, so no extra environment variables are needed. GitHub
Actions runs both commands on every pull request. See `tests/README.md` for the folder layout,
which follows the test-case IDs in the Test Plan.

## Settings

- `config/settings/base.py` contains shared settings.
- `config/settings/dev.py` contains development settings (the default for `manage.py`).
- `config/settings/test.py` contains the settings used by the automated tests.
- `config/settings/prod.py` contains production settings.

For production, set `DJANGO_SETTINGS_MODULE=config.settings.prod` and provide
`DJANGO_SECRET_KEY` and `DJANGO_ALLOWED_HOSTS` through the environment.
Production requires HTTPS: Django redirects insecure requests and sends a
one-year HSTS policy. The trusted TLS-terminating proxy must overwrite
`X-Forwarded-Proto` with the actual connection scheme before forwarding requests;
do not expose Django directly to clients that can supply this header. Configure
the ingress to accept TLS 1.2 or newer and reject plaintext traffic (or redirect
HTTP to HTTPS before proxying). TLS protocol negotiation is enforced by that
ingress, not by Django. Development and test settings continue to allow HTTP.

## Django apps

- `accounts` - authentication, accounts, profile and password reset
- `tasks` - tasks, labels, assignment and search
- `collab` - collaboration
- `dash` - dashboard
- `notif` - notifications
- `adminpanel` - user administration, audit records and the audit log
- `storage` - file storage

## Project documents

- `docs/schema.md` - the agreed data model
- `DEVIATIONS.md` - every place where what we build differs from the submitted SRS, SAD and
  Test Plan, with the reason
- `tests/README.md` - test layout and naming

## Contributing

- Branch from `dev`: `feature/<issue-number>-short-name`.
- Open the pull request against `dev` and fill in the template. Use `Part of #N` until the
  tester has run the test case by hand on the final commit; use `Closes #N` only after that.
- GitHub Actions (lint and tests) must pass. The repo owner reviews and merges with
  "Squash and merge".
- If your change differs from the SRS, SAD or Test Plan, add an entry to `DEVIATIONS.md`.
- Never commit `.env`, uploaded files (`media/`) or a virtual environment.
