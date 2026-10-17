# Task Manager Application

A Django task management application.

## Requirements

- Python 3.12 or newer
- pip

## Local development

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export DJANGO_SECRET_KEY="$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')"
python manage.py runserver
```
## Running tests

From the repository root, run:

```bash
python manage.py test
```

Open http://127.0.0.1:8000/ in your browser.

The development settings are loaded by default.
## Database and email services

For S-01, Django uses SQLite (`db.sqlite3`). Docker Compose defines PostgreSQL 16, which Django will be configured to use in S-02.

Copy the example environment file, then start PostgreSQL and MailHog:

```bash
cp .env.example .env
docker compose up -d db mailhog
```
PostgreSQL is available at 127.0.0.1:5432. MailHog receives email at 127.0.0.1:1025; view captured messages at http://127.0.0.1:8025/.
To stop the services, run docker compose down.

## Settings

Settings are split into three files:

- `config/settings/base.py` contains shared settings.
- `config/settings/dev.py` contains development settings.
- `config/settings/prod.py` contains production settings.

For production, set `DJANGO_SETTINGS_MODULE=config.settings.prod` and provide `DJANGO_SECRET_KEY` and `DJANGO_ALLOWED_HOSTS` through the environment.

## Django apps

- `accounts` — authentication and user accounts
- `tasks` — tasks
- `collab` — collaboration
- `dash` — dashboard
- `notif` — notifications
- `adminpanel` — administration
- `storage` — file storage
