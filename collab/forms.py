from django import forms
from django.contrib.auth import get_user_model

from .models import TaskShare


class TaskShareForm(forms.Form):
    email = forms.EmailField(label="Share with")
    permission = forms.ChoiceField(choices=TaskShare.Permission.choices)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        user_model = get_user_model()
        try:
            self.user = user_model.objects.get(email__iexact=email)
        except user_model.DoesNotExist:
            raise forms.ValidationError("No account was found for that email address.") from None
        if not self.user.is_active or getattr(self.user, "deleted_at", None):
            raise forms.ValidationError("That account is disabled and cannot receive a share.")
        return email
