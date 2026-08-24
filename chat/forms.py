from django import forms
from .models import Message


ALLOWED_ATTACHMENT_EXTENSIONS = {"pdf", "doc", "docx", "xls", "xlsx", "csv", "png", "jpg", "jpeg", "zip"}
MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024  # 10 MB


class MessageForm(forms.ModelForm):
    attachment = forms.FileField(
        required=False,
        label="Attach file",
        help_text="PDF, Word, Excel, CSV, image, or ZIP — max 10 MB.",
        widget=forms.ClearableFileInput(attrs={"class": "msg-attachment-input"}),
    )

    class Meta:
        model = Message
        fields = ["body"]
        widgets = {
            "body": forms.Textarea(attrs={
                "rows": 2,
                "placeholder": "Type your message…",
                "class": "msg-input",
                "style": "width: 100%; box-sizing: border-box;",
            }),
        }

    def clean_attachment(self):
        f = self.cleaned_data.get("attachment")
        if not f:
            return f
        ext = f.name.rsplit(".", 1)[-1].lower() if "." in f.name else ""
        if ext not in ALLOWED_ATTACHMENT_EXTENSIONS:
            raise forms.ValidationError(
                "Only PDF, Word, Excel, CSV, image, or ZIP files are allowed."
            )
        if f.size > MAX_ATTACHMENT_SIZE:
            raise forms.ValidationError("Attachment must be 10 MB or smaller.")
        return f

    def clean(self):
        cleaned_data = super().clean()
        body = cleaned_data.get("body", "").strip()
        attachment = cleaned_data.get("attachment")
        if not body and not attachment:
            raise forms.ValidationError("Please enter a message or attach a file.")
        return cleaned_data
