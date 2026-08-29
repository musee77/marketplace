from django import forms
from .models import ContactMessage


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "category", "subject", "message"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Your full name",
                "required": True,
            }),
            "email": forms.EmailInput(attrs={
                "class": "form-control",
                "placeholder": "you@example.com",
                "required": True,
            }),
            "category": forms.Select(attrs={
                "class": "form-control",
                "required": True,
            }),
            "subject": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "What is your inquiry about?",
                "required": True,
            }),
            "message": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 5,
                "placeholder": "Describe your question, issue, or feedback in detail...",
                "required": True,
            }),
        }
        labels = {
            "name": "Full Name",
            "email": "Email Address",
            "category": "Inquiry Topic",
            "subject": "Subject",
            "message": "Message",
        }
