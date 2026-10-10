# Test Environment Setup

1. Install Docker Desktop.
2. Copy `.env.example` to `.env`.
3. Run `docker compose up -d`.
4. MailHog inbox: http://localhost:8025
5. Seed data (once the Django models are merged): `python manage.py seed_test_data`

## Test accounts (test-only passwords)

| Role            | Email           |
|-----------------|-----------------|
| Team Member     | member@test.com |
| Project Manager | pm@test.com     |
| Administrator   | admin@test.com  |

Seed data includes sample tasks in each status: To Do, In Progress, Blocked, Completed.
