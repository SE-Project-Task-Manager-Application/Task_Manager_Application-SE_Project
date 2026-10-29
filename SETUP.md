# Test Environment Setup


## 1. Start the services

1. Install Docker Desktop.
2. Copy `.env.example` to `.env`:
   - Windows: `copy .env.example .env`
   - Mac/Linux: `cp .env.example .env`
   - Then set your own Django secret key: run `python -c "import secrets; print(secrets.token_urlsafe(50))"` and replace the `DJANGO_SECRET_KEY` value in your `.env` with the result. `.env` is private and ignored by Git; never commit it or share your key.
3. Run `docker compose up -d`.
4. MailHog inbox: http://localhost:8025

## 2. Run the app

1. Create and activate a virtual environment:
   - Windows: `python -m venv venv` then `venv\Scripts\activate`
   - Mac/Linux: `python -m venv venv` then `source venv/bin/activate`
2. Install dependencies: `pip install -r requirements.txt`
3. Apply migrations: `python manage.py migrate`
4. Start the server: `python manage.py runserver`

## 3. Stop and reset

- Stop the containers: `docker compose down`
- Wipe the database as well (deletes all data): `docker compose down -v`

## Test accounts (test-only passwords)

| Role            | Email                |
|-----------------|----------------------|
| Team Member     | member@example.com   |
| Project Manager | pm@example.com       |
| Administrator   | admin@example.com    |

Password for all test accounts: `SEPROG123`

These accounts do not exist yet. Seed data is coming in a later update (S-07b), and the seed script will use the same password as above.
