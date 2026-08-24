from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.hashers import make_password
from .models import User, SpecialistProfile, ClientProfile
import uuid


class SignUpForm(forms.Form):
    """
    Minimal sign-up form: email, role, optional referral code, password (single field).
    Username is auto-generated from the email local-part to satisfy AbstractUser.
    """
    email = forms.EmailField(
        required=True,
        label="Email address",
        widget=forms.EmailInput(attrs={"placeholder": "you@example.com", "autocomplete": "email"}),
    )
    role = forms.ChoiceField(
        choices=[
            (User.Role.CLIENT, "Client — I want to hire"),
            (User.Role.SPECIALIST, "Specialist — I want to work"),
        ],
        label="I want to…",
    )
    referral_code = forms.CharField(
        max_length=20,
        required=False,
        label="Referral code (optional)",
        widget=forms.TextInput(attrs={"placeholder": "e.g. REF123456"}),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        min_length=8,
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_referral_code(self):
        code = self.cleaned_data.get("referral_code", "").strip().upper()
        if code and not User.objects.filter(referral_code=code).exists():
            raise forms.ValidationError("Invalid referral code. Please check or leave blank.")
        return code

    @staticmethod
    def _unique_username(email):
        """Derive a unique username from the email local-part."""
        base = email.split("@")[0][:30]
        username = base
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base}{counter}"
            counter += 1
        return username

    def save(self, commit=True):
        data = self.cleaned_data
        user = User(
            username=self._unique_username(data["email"]),
            email=data["email"],
            role=data["role"],
            password=make_password(data["password"]),
        )
        ref_code = data.get("referral_code")
        if ref_code:
            referrer = User.objects.filter(referral_code=ref_code).first()
            if referrer:
                user.referred_by = referrer
        if commit:
            user.save()
            if user.role == User.Role.SPECIALIST:
                SpecialistProfile.objects.create(user=user)
            else:
                ClientProfile.objects.create(user=user)
        return user


class SpecialistProfileForm(forms.ModelForm):
    class Meta:
        model = SpecialistProfile
        fields = ["headline", "bio", "skills", "hourly_rate", "years_experience", "location", "is_available", "portfolio_url", "avatar"] 

    avatar = forms.ImageField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop("avatar", None)  # avatar lives on User; kept off this form


class ClientProfileForm(forms.ModelForm):
    class Meta:
        model = ClientProfile
        fields = ["company_name", "bio", "location"]


class SpecialistFinancialForm(forms.ModelForm):
    class Meta:
        model = SpecialistProfile
        fields = ["payout_method", "payout_details"]


class ClientFinancialForm(forms.ModelForm):
    class Meta:
        model = ClientProfile
        fields = ["billing_address", "default_payment_method"]


class UserBasicForm(forms.ModelForm):
    email = forms.EmailField(
        required=True,
        disabled=True,
        help_text="Email addresses cannot be changed from your profile.",
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone", "avatar"]


class AddFundsForm(forms.Form):
    amount = forms.DecimalField(min_value=0.01, max_digits=10, decimal_places=2, label="Amount ($)")
    PAYMENT_METHODS = [
        ("PAYSTACK", "Paystack (Card, Mobile Money, Bank Transfer)"),
        ("MPESA", "M-Pesa"),
        ("PAYPAL", "PayPal"),
    ]
    payment_method = forms.ChoiceField(choices=PAYMENT_METHODS, initial="PAYSTACK", required=True, label="Payment Provider")
    reference = forms.CharField(max_length=200, required=False, help_text="Optional reference from your payment provider")
