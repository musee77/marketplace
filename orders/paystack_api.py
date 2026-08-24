import time
import requests
from decimal import Decimal
from django.conf import settings as django_settings


class PaystackError(Exception):
    pass


def _profile_contains_kenya(profile):
    if not profile:
        return False
    texts = []
    if getattr(profile, "location", None):
        texts.append(profile.location)
    if getattr(profile, "billing_address", None):
        texts.append(profile.billing_address)
    combined = " ".join(texts).lower()
    return "kenya" in combined


def get_currency_for_profile(profile):
    """Return USD currency for all transactions."""
    return getattr(django_settings, "PAYSTACK_CURRENCY", "USD") or "USD"


class PaystackAPI:
    @staticmethod
    def initialize_payment(amount, email, reference=None, client_profile=None, callback_url=None):
        """Initialize a Paystack transaction and return the gateway response.

        - `amount` is a Decimal or number in major units (e.g. 10.50 means $10.50 or Ksh10.50)
        - returns the parsed JSON response from Paystack when successful
        - raises PaystackError on failure
        """
        key = getattr(django_settings, "PAYSTACK_SECRET_KEY", None)
        if not key:
            raise PaystackError("Paystack not configured (PAYSTACK_SECRET_KEY missing)")

        # Determine currency
        currency = get_currency_for_profile(client_profile)

        # Paystack expects amount in the smallest currency unit (cents/kobo)
        try:
            amt = Decimal(amount)
        except Exception:
            raise PaystackError("Invalid amount")
        minor = int((amt * 100).to_integral_value())

        # Ensure email is in a valid format that Paystack accepts
        clean_email = (email or "").strip()
        if not clean_email or "@" not in clean_email or "." not in clean_email.split("@")[-1]:
            safe_prefix = "".join(c for c in clean_email if c.isalnum()) or f"customer_{int(time.time())}"
            clean_email = f"{safe_prefix}@datahire.test"

        payload = {
            "email": clean_email,
            "amount": minor,
        }
        if currency:
            payload["currency"] = currency
        if reference:
            payload["reference"] = reference
        if callback_url:
            payload["callback_url"] = callback_url
        headers = {"Authorization": f"Bearer {key}"}

        url = "https://api.paystack.co/transaction/initialize"
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=15)
        except Exception as e:
            raise PaystackError(f"Network error initializing Paystack payment: {e}")

        if resp.status_code != 200:
            raise PaystackError(f"Paystack initialization failed: HTTP {resp.status_code} {resp.text}")

        data = resp.json()
        if not data.get("status"):
            raise PaystackError(f"Paystack error: {data.get('message')}")

        # return the full payload — caller will handle authorization_url/reference
        return data.get("data", {})

    @staticmethod
    def verify_payment(reference):
        """Verify a Paystack transaction by reference and return data dict.

        Raises PaystackError on failure.
        """
        key = getattr(django_settings, "PAYSTACK_SECRET_KEY", None)
        if not key:
            raise PaystackError("Paystack not configured (PAYSTACK_SECRET_KEY missing)")

        url = f"https://api.paystack.co/transaction/verify/{reference}"
        headers = {"Authorization": f"Bearer {key}"}
        try:
            resp = requests.get(url, headers=headers, timeout=15)
        except Exception as e:
            raise PaystackError(f"Network error verifying Paystack payment: {e}")

        if resp.status_code != 200:
            raise PaystackError(f"Paystack verify failed: HTTP {resp.status_code} {resp.text}")

        data = resp.json()
        if not data.get("status"):
            raise PaystackError(f"Paystack verify error: {data.get('message')}")

        return data.get("data", {})
