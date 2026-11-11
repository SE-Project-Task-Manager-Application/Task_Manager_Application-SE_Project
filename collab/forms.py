from django import forms

from .models import COMMENT_MAX_LENGTH


class CommentForm(forms.Form):
    body = forms.CharField(
        label="Add a comment",
        max_length=COMMENT_MAX_LENGTH,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text=f"Up to {COMMENT_MAX_LENGTH} characters.",
    )
