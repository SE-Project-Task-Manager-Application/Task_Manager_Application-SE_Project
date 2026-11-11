from django.core.exceptions import ValidationError

from .config import get_system_config


class DatabasePasswordLengthValidator:
    def validate(self, password, user=None):
        minimum = get_system_config().password_min_length
        if len(password) < minimum:
            raise ValidationError(f"This password must contain at least {minimum} characters.")

    def get_help_text(self):
        minimum = get_system_config().password_min_length
        return f"Your password must contain at least {minimum} characters."
