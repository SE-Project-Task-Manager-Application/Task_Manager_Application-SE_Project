# Task Manager Application

A Django task management application.

## Requirements

- Python 3
- pip

## Local development

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export DJANGO_SECRET_KEY="$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')"
python manage.py migrate
python manage.py runserver
```

Open http://127.0.0.1:8000/ in your browser.

The development settings are loaded by default. They use the local development database configuration.

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