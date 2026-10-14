import os

from .base import *  # noqa: F403

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]