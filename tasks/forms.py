from django import forms
from django.contrib.auth import get_user_model

from .models import Label, Task
from .services import can_assign


class TaskForm(forms.ModelForm):
    """Task fields shared by creation and stale-safe editing.

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
    expected_version = forms.IntegerField(widget=forms.HiddenInput, required=False)

    class Meta:
        model = Task
        fields = [
            "title",
            "description",
            "due_date",
            "priority",
            "status",
            "labels",
            "expected_version",
        ]

    def __init__(self, *args, user, include_status=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["labels"].queryset = Label.objects.filter(is_archived=False)
        if not include_status:
            self.fields.pop("status")
        if can_assign(user):
            user_model = get_user_model()
            self.fields["assignees"] = forms.ModelMultipleChoiceField(
                queryset=user_model.objects.filter(
                    is_active=True, deleted_at__isnull=True
                ).order_by("email"),
                required=False,
                widget=forms.CheckboxSelectMultiple,
                label="Assign to",
            )
            self.fields["assignees"].label_from_instance = lambda person: person.email


class TaskCreateForm(TaskForm):
    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, user=user, **kwargs)
