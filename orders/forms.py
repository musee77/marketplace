from django import forms
from .models import Order, Offer, OrderDocument
from chat.models import Message
from services.models import Service


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_clean = super().clean
        if not data:
            return []
        files = data if isinstance(data, (list, tuple)) else [data]
        return [single_clean(upload, initial) for upload in files]


class OrderCreateForm(forms.ModelForm):
    service = forms.ModelChoiceField(queryset=Service.objects.filter(is_active=True), required=True)
    attachments = MultipleFileField(
        required=False,
        label="Reference documents",
        help_text="Optional: PDF, Word, Excel, CSV, image, or ZIP files up to 10 MB each.",
    )

    class Meta:
        model = Order
        fields = ["service", "requirements", "due_date"]
        widgets = {"due_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # show active services only, ordered by newest
        self.fields["service"].queryset = Service.objects.filter(is_active=True).select_related("specialist").order_by("-created_at")
        self.fields["service"].label_from_instance = lambda obj: f"{obj.title} — {obj.specialist.get_full_name() or obj.specialist.username} (${obj.price})"
        # include payment method choices
        self.fields["payment_method"] = forms.ChoiceField(choices=Order.PAYMENT_METHODS, initial=Order.PAYMENT_METHODS[0][0])

    def clean_attachments(self):
        allowed_extensions = {"pdf", "doc", "docx", "xls", "xlsx", "csv", "png", "jpg", "jpeg", "zip"}
        cleaned_files = []
        for uploaded_file in self.cleaned_data.get("attachments", []):
            extension = uploaded_file.name.rsplit(".", 1)[-1].lower() if "." in uploaded_file.name else ""
            if extension not in allowed_extensions:
                raise forms.ValidationError("Upload a PDF, document, spreadsheet, CSV, image, or ZIP file.")
            if uploaded_file.size > 10 * 1024 * 1024:
                raise forms.ValidationError("Each document must be 10 MB or smaller.")
            cleaned_files.append(uploaded_file)
        return cleaned_files


class OfferCreateForm(forms.ModelForm):
    """Form for specialists to send offers to clients."""
    service = forms.ModelChoiceField(
        queryset=Service.objects.none(),
        required=True,
        label="Choose listing",
        help_text="Select the specialist service this offer is for.",
    )

    class Meta:
        model = Offer
        fields = ["service", "title", "description", "price", "delivery_days"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "e.g., Data Analysis Report", "class": "form-control"}),
            "description": forms.Textarea(attrs={"placeholder": "Describe what you're offering...", "rows": 5, "class": "form-control"}),
            "price": forms.NumberInput(attrs={"placeholder": "0.00", "step": "0.01", "class": "form-control"}),
            "delivery_days": forms.NumberInput(attrs={"min": "1", "class": "form-control"}),
        }
        labels = {
            "title": "Offer Title",
            "description": "Description",
            "price": "Price (USD)",
            "delivery_days": "Delivery Days",
        }

    def __init__(self, *args, specialist=None, **kwargs):
        super().__init__(*args, **kwargs)
        if specialist is not None:
            self.fields["service"].queryset = Service.objects.filter(specialist=specialist, is_active=True)


class OfferMessageForm(forms.ModelForm):
    """Edit fields for a specialist's pending chat offer."""
    service = forms.ModelChoiceField(queryset=Service.objects.none(), required=True, label="Listing")

    class Meta:
        model = Message
        fields = ["offer_title", "offer_description", "offer_price", "offer_delivery_days"]
        widgets = {
            "offer_title": forms.TextInput(attrs={"placeholder": "e.g., Data Analysis Report", "class": "form-control"}),
            "offer_description": forms.Textarea(attrs={"placeholder": "Describe what you're offering...", "rows": 5, "class": "form-control"}),
            "offer_price": forms.NumberInput(attrs={"placeholder": "0.00", "step": "0.01", "class": "form-control"}),
            "offer_delivery_days": forms.NumberInput(attrs={"min": "1", "class": "form-control"}),
        }
        labels = {
            "offer_title": "Offer Title",
            "offer_description": "Description",
            "offer_price": "Price (USD)",
            "offer_delivery_days": "Delivery Days",
        }

    def __init__(self, *args, specialist=None, **kwargs):
        super().__init__(*args, **kwargs)
        if specialist is not None:
            self.fields["service"].queryset = Service.objects.filter(specialist=specialist, is_active=True)
        if self.instance and self.instance.offer_service_id:
            self.fields["service"].initial = self.instance.offer_service_id

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.offer_service = self.cleaned_data["service"]
        if commit:
            instance.save()
        return instance


class OrderDocumentForm(forms.ModelForm):
    class Meta:
        model = OrderDocument
        fields = ["title", "file"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "e.g., Final report", "class": "form-control"}),
            "file": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

    def clean_file(self):
        uploaded_file = self.cleaned_data["file"]
        allowed_extensions = {"pdf", "doc", "docx", "xls", "xlsx", "csv", "png", "jpg", "jpeg", "zip"}
        extension = uploaded_file.name.rsplit(".", 1)[-1].lower() if "." in uploaded_file.name else ""
        if extension not in allowed_extensions:
            raise forms.ValidationError("Upload a PDF, document, spreadsheet, CSV, image, or ZIP file.")
        if uploaded_file.size > 10 * 1024 * 1024:
            raise forms.ValidationError("Documents must be 10 MB or smaller.")
        return uploaded_file


class DeliverOrderForm(forms.Form):
    """
    Specialist submits this form to mark an order as DELIVERED.
    At least one delivery document file is required.
    Additional files can be attached via the `files` multi-file field.
    """
    delivery_note = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            "rows": 4,
            "placeholder": "Describe what you've delivered…",
            "class": "form-control",
        }),
        label="Delivery note",
        help_text="Summarise the work you've completed for the client.",
    )
    files = MultipleFileField(
        required=True,
        label="Delivery file(s)",
        help_text="Attach at least one file to deliver your work. PDF, Word, Excel, CSV, image, or ZIP — max 10 MB each.",
        widget=MultipleFileInput(attrs={"class": "form-control"}),
    )

    def clean_files(self):
        allowed_extensions = {"pdf", "doc", "docx", "xls", "xlsx", "csv", "png", "jpg", "jpeg", "zip"}
        cleaned = []
        for f in self.cleaned_data.get("files", []):
            ext = f.name.rsplit(".", 1)[-1].lower() if "." in f.name else ""
            if ext not in allowed_extensions:
                raise forms.ValidationError("Only PDF, Word, Excel, CSV, image, or ZIP files are allowed.")
            if f.size > 10 * 1024 * 1024:
                raise forms.ValidationError(f"'{f.name}' exceeds the 10 MB limit.")
            cleaned.append(f)
        if not cleaned:
            raise forms.ValidationError("You must attach at least one file to deliver your work.")
        return cleaned


class RequestRevisionForm(forms.Form):
    """
    Client submits this form to request a revision.
    Instructions are required — the client must explain what needs to change.
    """
    instructions = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            "rows": 5,
            "placeholder": "Describe what you'd like the specialist to change or correct…",
            "class": "form-control",
        }),
        label="Revision instructions",
        help_text="Provide clear details on what you want the specialist to modify or correct.",
    )
