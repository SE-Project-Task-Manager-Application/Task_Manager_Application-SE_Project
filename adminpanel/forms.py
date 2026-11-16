from django import forms

from tasks.models import Label

from .models import SystemConfig


class SystemConfigForm(forms.ModelForm):
    class Meta:
        model = SystemConfig
        fields = (
            "password_min_length",
            "session_timeout_seconds",
            "notifications_enabled",
            "notification_sender",
        )
        help_texts = {
            "password_min_length": "Minimum length for newly chosen passwords.",
            "session_timeout_seconds": "Session inactivity timeout in seconds.",
        }

    def clean_password_min_length(self):
        value = self.cleaned_data["password_min_length"]
        if value < 8 or value > 256:
            raise forms.ValidationError("Password length must be between 8 and 256.")
        return value

    def clean_session_timeout_seconds(self):
        value = self.cleaned_data["session_timeout_seconds"]
        if value < 300 or value > 86400:
            raise forms.ValidationError("Session timeout must be between 5 minutes and 24 hours.")
        return value


class LabelForm(forms.ModelForm):
    """Create or rename a category (TM-F-051)."""

    class Meta:
        model = Label
        fields = ["name"]
        labels = {"name": "Category name"}

    def clean_name(self):
        name = " ".join(self.cleaned_data["name"].split())
        clash = Label.objects.filter(name__iexact=name)
        if self.instance.pk:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise forms.ValidationError("A category with this name already exists.")
        return name
