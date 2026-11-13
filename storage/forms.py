from django import forms

from .services import scan_attachment


class AttachmentForm(forms.Form):
    file = forms.FileField()

    def clean_file(self):
        upload = self.cleaned_data["file"]
        valid, message = scan_attachment(upload)
        if not valid:
            raise forms.ValidationError(message)
        return upload
