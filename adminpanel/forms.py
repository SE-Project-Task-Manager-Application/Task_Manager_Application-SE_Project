from django import forms

from tasks.models import Label


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
