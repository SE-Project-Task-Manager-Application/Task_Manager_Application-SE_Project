from django import forms
from django.contrib.auth import get_user_model

from .models import Label, Task
from .services import can_assign


class TaskCreateForm(forms.ModelForm):
    """TM-F-010: title, description, due date and priority, plus optional labels.

    The assignees field only exists for a Project Manager (SAD 4.3); the service
    re-checks the role, so a hand-made POST cannot get around it.
    """

    due_date = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d"],
        help_text="Optional.",
    )
    labels = forms.ModelMultipleChoiceField(
        queryset=Label.objects.none(), required=False, widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = Task
        fields = ["title", "description", "due_date", "priority", "labels"]

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["labels"].queryset = Label.objects.filter(is_archived=False)
        if can_assign(user):
            user_model = get_user_model()
            self.fields["assignees"] = forms.ModelMultipleChoiceField(
                queryset=user_model.objects.filter(is_active=True, deleted_at__isnull=True)
                .order_by("email"),
                required=False,
                widget=forms.CheckboxSelectMultiple,
                label="Assign to",
            )
            self.fields["assignees"].label_from_instance = lambda person: person.email
