from django.core.exceptions import ValidationError

from .models import SystemConfig


class DatabasePasswordLengthValidator:
    def validate(self, password, user=None):
        config = SystemConfig.objects.first()
        minimum = config.password_min_length if config else 8
        if len(password) < minimum:
            raise ValidationError(f"This password must contain at least {minimum} characters.")

    def get_help_text(self):
        config = SystemConfig.objects.first()
        minimum = config.password_min_length if config else 8
        return f"Your password must contain at least {minimum} characters."
