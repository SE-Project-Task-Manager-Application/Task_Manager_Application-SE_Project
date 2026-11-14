from django import forms
from django.contrib.auth import get_user_model

from .models import COMMENT_MAX_LENGTH, TaskShare


class TaskShareForm(forms.Form):
    email = forms.EmailField(label="Share with")
    permission = forms.ChoiceField(choices=TaskShare.Permission.choices)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        user_model = get_user_model()
        matches = list(user_model.objects.filter(email__iexact=email).order_by("pk")[:2])
        if not matches:
            raise forms.ValidationError("No account was found for that email address.") from None
        if len(matches) > 1:
            raise forms.ValidationError(
                "More than one account matches that email address. Contact an administrator."
            )
        self.user = matches[0]
        if not self.user.is_active or getattr(self.user, "deleted_at", None):
            raise forms.ValidationError("That account is disabled and cannot receive a share.")
        return email


class CommentForm(forms.Form):
    body = forms.CharField(
        label="Add a comment",
        max_length=COMMENT_MAX_LENGTH,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text=f"Up to {COMMENT_MAX_LENGTH} characters.",
    )
