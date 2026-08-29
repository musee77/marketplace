from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.db import models
from django.views.generic import DetailView
from django.urls import reverse_lazy, reverse

from .forms import SignUpForm, SpecialistProfileForm, ClientProfileForm, UserBasicForm
from .models import User, SpecialistProfile, ClientProfile, DepositTransaction
from .forms import SpecialistFinancialForm, ClientFinancialForm, AddFundsForm
from django.conf import settings as django_settings
import time
import random
from orders.paystack_api import PaystackAPI, PaystackError
from django.contrib.auth import authenticate
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from orders.models import Order
from reviews.models import Review
from decimal import Decimal, InvalidOperation


@csrf_protect
def signup_view(request):
    if request.user.is_authenticated:
        messages.warning(request, "Please log out first before creating a new account.")
        return redirect("core:dashboard")

    ref = request.GET.get("ref", "").strip().upper()
    referrer = User.objects.filter(referral_code=ref).first() if ref else None

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='accounts.backends.EmailBackend')
            if user.referred_by:
                messages.success(request, f"Welcome to Synovae! You were invited by {user.referred_by.get_full_name() or user.referred_by.username} and qualify for reduced platform fees.")
            else:
                messages.success(request, f"Welcome to Synovae, {user.username}!")
            return redirect("core:dashboard")
    else:
        initial = {"referral_code": ref} if ref else {}
        form = SignUpForm(initial=initial)

    return render(request, "accounts/signup.html", {
        "form": form,
        "referrer": referrer,
        "ref_code": ref,
    })



@login_required
def referrals_view(request):
    user = request.user
    referral_link = request.build_absolute_uri(reverse("accounts:signup") + f"?ref={user.referral_code}")
    referred_qs = user.referrals.select_related("specialist_profile", "client_profile").order_by("-date_created")
    referral_orders = user.referral_orders.select_related("client", "service").order_by("-created_at")

    paginator = Paginator(referred_qs, 10)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    return render(request, "accounts/referrals.html", {
        "referral_code": user.referral_code,
        "referral_link": referral_link,
        "referred_users": page_obj.object_list,
        "page_obj": page_obj,
        "referral_orders": referral_orders,
        "total_referrals": user.referral_count,
        "total_orders": user.referral_orders_count,
        "total_earnings": user.referral_earnings_total,
    })

def specialist_list(request):
    specialists = SpecialistProfile.objects.filter(
        is_approved=True,
    ).select_related("user").prefetch_related("user__services__category")
    query = request.GET.get("q", "").strip()
    if query:
        specialists = specialists.filter(
            models.Q(headline__icontains=query)
            | models.Q(bio__icontains=query)
            | models.Q(skills__icontains=query)
            | models.Q(location__icontains=query)
            | models.Q(user__username__icontains=query)
            | models.Q(user__first_name__icontains=query)
            | models.Q(user__last_name__icontains=query)
            | models.Q(user__services__title__icontains=query)
        ).distinct()
    page_obj = Paginator(specialists, 12).get_page(request.GET.get("page"))
    # Attach a random sample of 1-5 active listings to each profile on the page
    for profile in page_obj:
        active_services = [s for s in profile.user.services.all() if s.is_active]
        count = random.randint(1, min(5, len(active_services))) if active_services else 0
        profile.random_listings = random.sample(active_services, count) if count else []
        if profile.skills:
            profile.skills_list = [s.strip() for s in profile.skills.split(",") if s.strip()][:4]
        else:
            profile.skills_list = []
    return render(request, "accounts/specialist_list.html", {
        "page_obj": page_obj,
        "q": query,
    })



@csrf_protect
def login_view(request):
    if request.user.is_authenticated:
        messages.warning(request, "You are already logged in. Log out first to switch accounts.")
        return redirect("core:dashboard")

    error = None
    next_url = request.POST.get("next") or request.GET.get("next")
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        user = authenticate(request, username=email, password=password)
        if user is None:
            try:
                user_obj = User.objects.get(email=email)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None

        if user is not None:
            if user.is_suspended:
                error = "This account has been suspended."
            else:
                login(request, user)
                messages.success(request, f"Welcome back, {user.first_name or user.username}!")
                if user.is_staff or user.is_superuser or user.role == User.Role.MANAGER:
                    return redirect("/admin/")
                if next_url and url_has_allowed_host_and_scheme(
                    next_url,
                    allowed_hosts={request.get_host()},
                    require_https=request.is_secure(),
                ):
                    return redirect(next_url)
                return redirect("core:dashboard")
        else:
            error = "Invalid email or password."

    return render(request, "accounts/login.html", {"error": error, "next": next_url})


@login_required
def edit_profile(request):
    user = request.user
    edit_mode = request.GET.get("edit") == "1" or request.method == "POST"
    active_tab = "panel-account"
    user_form = UserBasicForm(instance=user)
    profile_form = None
    financial_form = None
    password_form = PasswordChangeForm(user)
    # ranking info
    ranking = None
    total_orders = 0
    profile_reviews = Review.objects.none()
    if user.is_specialist:
        profile, _ = SpecialistProfile.objects.get_or_create(user=user)
        profile_form = SpecialistProfileForm(instance=profile)
        ranking = {"average": profile.average_rating, "reviews": profile.review_count}
        total_orders = Order.objects.filter(specialist=user).count()
        profile_reviews = user.reviews_received.select_related("reviewer", "service").order_by("-created_at")
        financial_form = SpecialistFinancialForm(instance=profile)
    elif user.is_client:
        profile, _ = ClientProfile.objects.get_or_create(user=user)
        profile_form = ClientProfileForm(instance=profile)
        total_orders = Order.objects.filter(client=user).count()

    if request.method == "POST":
        action = request.POST.get("form_action") or request.POST.get("action")
        saved = False

        if "submit_specialization" in request.POST or action == "specialization":
            active_tab = "panel-specialization"
            if user.is_specialist:
                profile_form = SpecialistProfileForm(request.POST, instance=profile)
                if profile_form.is_valid():
                    if profile_form.has_changed():
                        profile_obj = profile_form.save(commit=False)
                        profile_obj.is_approved = False
                        profile_obj.save()
                        messages.success(request, "Specialization details updated and submitted for manager approval.")
                    else:
                        messages.info(request, "No changes made to specialization details.")
                    return redirect(reverse("accounts:edit_profile") + "#panel-specialization")
        elif "submit_financials" in request.POST or action == "financials":
            active_tab = "panel-financials"
            if user.is_specialist and financial_form:
                financial_form = SpecialistFinancialForm(request.POST, instance=profile)
                if financial_form.is_valid():
                    financial_form.save()
                    messages.success(request, "Financial details updated.")
                    return redirect(reverse("accounts:edit_profile") + "#panel-financials")
        elif "submit_account" in request.POST or action == "account":
            active_tab = "panel-account"
            user_form = UserBasicForm(request.POST, request.FILES, instance=user)
            if user.is_client and profile_form:
                profile_form = ClientProfileForm(request.POST, instance=profile)
                if user_form.is_valid() and profile_form.is_valid():
                    user_form.save()
                    profile_form.save()
                    messages.success(request, "Account details updated.")
                    return redirect("accounts:edit_profile")
            else:
                if user_form.is_valid():
                    user_form.save()
                    messages.success(request, "Account details updated.")
                    return redirect("accounts:edit_profile")
        else:
            # Fallback for generic multi-form submission or automated tests
            user_form = UserBasicForm(request.POST, request.FILES, instance=user)
            if user.is_specialist:
                profile_form = SpecialistProfileForm(request.POST, instance=profile)
                financial_form = SpecialistFinancialForm(request.POST, instance=profile)
            elif user.is_client:
                profile_form = ClientProfileForm(request.POST, instance=profile)

            if user_form.is_valid():
                user_form.save()
                saved = True
            if profile_form and profile_form.is_valid():
                if user.is_specialist and profile_form.has_changed():
                    profile_obj = profile_form.save(commit=False)
                    profile_obj.is_approved = False
                    profile_obj.save()
                else:
                    profile_form.save()
                saved = True
            if financial_form and financial_form.is_valid():
                financial_form.save()
                saved = True
            if saved:
                messages.success(request, "Profile updated.")
                return redirect("accounts:edit_profile")

    return render(
        request,
        "accounts/edit_profile.html",
        {
            "user_form": user_form,
            "profile_form": profile_form,
            "financial_form": financial_form,
            "password_form": password_form,
            "ranking": ranking,
            "total_orders": total_orders,
            "active_tab": active_tab,
            "profile_reviews": profile_reviews,
            "edit_mode": edit_mode,
        },
    )


@login_required
def password_change(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password updated.")
            return redirect("accounts:edit_profile")
        else:
            # re-render edit_profile with form errors
            user = request.user
            user_form = UserBasicForm(instance=user)
            profile_form = None
            financial_form = None
            if user.is_specialist:
                profile, _ = SpecialistProfile.objects.get_or_create(user=user)
                profile_form = SpecialistProfileForm(instance=profile)
                financial_form = SpecialistFinancialForm(instance=profile)
                ranking = {"average": profile.average_rating, "reviews": profile.review_count}
            elif user.is_client:
                profile, _ = ClientProfile.objects.get_or_create(user=user)
                profile_form = ClientProfileForm(instance=profile)
                ranking = None
            total_orders = Order.objects.filter(client=user).count() if user.is_client else Order.objects.filter(specialist=user).count()
            return render(
                request,
                "accounts/edit_profile.html",
                {
                    "user_form": user_form,
                    "profile_form": profile_form,
                    "financial_form": financial_form,
                    "password_form": form,
                    "ranking": ranking,
                    "total_orders": total_orders,
                    "active_tab": "panel-settings",
                },
            )
    return redirect("accounts:edit_profile")


def logged_out(request):
    return render(request, "accounts/logged_out.html")


def logout_view(request):
    is_admin = request.user.is_authenticated and (
        request.user.is_staff or request.user.is_superuser or request.user.role == User.Role.MANAGER
    )
    referer = request.META.get("HTTP_REFERER", "")
    is_admin_page = "/admin/" in referer or "admin" in request.path

    logout(request)

    if is_admin or is_admin_page:
        messages.success(request, "Logged out from admin panel.")
        return redirect("/admin/login/")

    messages.success(request, "You have been logged out.")
    return redirect("accounts:logged_out")


class SpecialistPublicProfileView(DetailView):
    model = SpecialistProfile
    template_name = "accounts/specialist_public.html"
    context_object_name = "profile"
    pk_url_kwarg = "pk"

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not request.user.is_authenticated or request.user.pk != self.object.user_id:
            return redirect(self.object.get_absolute_url())

        form = SpecialistProfileForm(request.POST, instance=self.object)
        if form.is_valid():
            profile = form.save(commit=False)
            if form.has_changed():
                profile.is_approved = False
                profile.save()
                messages.success(request, "Specialist profile updated and submitted for approval.")
            else:
                messages.info(request, "No changes made to your specialist profile.")
            return redirect(self.object.get_absolute_url())

        context = self.get_context_data(form=form, edit_mode=True)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["services"] = self.object.user.services.filter(is_active=True).select_related("category")
        ctx["reviews"] = self.object.user.reviews_received.select_related("reviewer", "service").order_by("-created_at")[:3]
        ctx["listing_count"] = ctx["services"].count()
        ctx["review_count"] = self.object.user.reviews_received.count()
        ctx["average_rating"] = self.object.average_rating
        ctx["skills_list"] = [s.strip() for s in (self.object.skills or "").split(",") if s.strip()]
        ctx["edit_mode"] = self.request.GET.get("edit") == "1"
        if "form" not in ctx:
            ctx["form"] = SpecialistProfileForm(instance=self.object)
        return ctx


def specialist_reviews(request, pk):
    profile = get_object_or_404(SpecialistProfile.objects.select_related("user"), pk=pk)
    reviews = profile.user.reviews_received.select_related("reviewer", "service").order_by("-created_at")
    page_obj = Paginator(reviews, 10).get_page(request.GET.get("page"))
    return render(request, "accounts/specialist_reviews.html", {
        "profile": profile,
        "reviews": page_obj.object_list,
        "page_obj": page_obj,
        "review_count": reviews.count(),
        "average_rating": profile.average_rating,
        "listing_count": profile.user.services.filter(is_active=True).count(),
    })


def is_manager(user):
    return user.is_authenticated and user.is_manager


@user_passes_test(is_manager)
def manager_user_list(request):
    role_filter = request.GET.get("role", "")
    users = User.objects.exclude(id=request.user.id).order_by("-date_created")
    if role_filter:
        users = users.filter(role=role_filter)
    paginator = Paginator(users, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "accounts/manager_user_list.html", {"users": page_obj, "page_obj": page_obj, "role_filter": role_filter, "roles": User.Role.choices})


@user_passes_test(is_manager)
def manager_toggle_suspend(request, pk):
    target = get_object_or_404(User, pk=pk)
    if target.is_manager and not request.user.is_superuser:
        messages.error(request, "You cannot suspend another manager.")
        return redirect("accounts:manager_user_list")
    target.is_suspended = not target.is_suspended
    target.save(update_fields=["is_suspended"])
    messages.success(request, f"{target.username} is now {'suspended' if target.is_suspended else 'active'}.")
    return redirect("accounts:manager_user_list")


@user_passes_test(is_manager)
def manager_toggle_verify(request, pk):
    profile = get_object_or_404(SpecialistProfile, pk=pk)
    profile.is_verified = not profile.is_verified
    profile.save(update_fields=["is_verified"])
    messages.success(request, f"{profile.user.username} is now {'verified' if profile.is_verified else 'unverified'}.")
    return redirect("accounts:manager_user_list")


@user_passes_test(is_manager)
def manager_promote(request, pk):
    """Promote a user to manager, or demote back to client."""
    target = get_object_or_404(User, pk=pk)
    if not request.user.is_superuser:
        messages.error(request, "Only a superuser can change manager status.")
        return redirect("accounts:manager_user_list")
    if target.role == User.Role.MANAGER:
        target.role = User.Role.CLIENT
        ClientProfile.objects.get_or_create(user=target)
    else:
        target.role = User.Role.MANAGER
    target.save(update_fields=["role"])
    messages.success(request, f"{target.username}'s role updated to {target.get_role_display()}.")
    return redirect("accounts:manager_user_list")


@user_passes_test(is_manager)
def manager_delete_user(request, pk):
    target = get_object_or_404(User, pk=pk)
    if target.id == request.user.id:
        messages.error(request, "You cannot delete your own account.")
        return redirect("accounts:manager_user_list")
    if target.is_manager and not request.user.is_superuser:
        messages.error(request, "Only a superuser can delete another manager.")
        return redirect("accounts:manager_user_list")
    if request.method == "POST":
        username = target.username
        target.delete()
        messages.success(request, f"User '{username}' has been permanently deleted.")
    return redirect("accounts:manager_user_list")


@user_passes_test(is_manager)
def manager_pending_specialists(request):
    pending = SpecialistProfile.objects.filter(is_approved=False).select_related("user")
    paginator = Paginator(pending, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "accounts/pending_specialists.html", {"pending": page_obj, "page_obj": page_obj})


@user_passes_test(is_manager)
def manager_toggle_approve(request, pk):
    profile = get_object_or_404(SpecialistProfile, pk=pk)
    profile.is_approved = not profile.is_approved
    profile.save(update_fields=["is_approved"])
    status = "approved" if profile.is_approved else "unapproved"
    messages.success(request, f"{profile.user.get_full_name() or profile.user.username} is now {status}.")
    return redirect(request.META.get("HTTP_REFERER") or "accounts:pending_specialists")


@user_passes_test(is_manager)
def manager_manage_balance(request, pk):
    target = get_object_or_404(User, pk=pk)
    profile, _ = SpecialistProfile.objects.get_or_create(user=target)
    if request.method == "POST":
        action = request.POST.get("action")
        amount_raw = request.POST.get("amount")
        try:
            amt = Decimal(amount_raw)
        except (InvalidOperation, TypeError):
            messages.error(request, "Invalid amount.")
            return redirect("accounts:manager_manage_balance", pk=pk)

        if action == "credit":
            profile.balance = (profile.balance or Decimal('0')) + amt
            profile.save(update_fields=["balance"])
            messages.success(request, f"Credited ${amt} to {target.username}.")
        elif action == "debit":
            profile.balance = (profile.balance or Decimal('0')) - amt
            profile.save(update_fields=["balance"])
            messages.success(request, f"Debited ${amt} from {target.username}.")
        elif action == "set":
            profile.balance = amt
            profile.save(update_fields=["balance"])
            messages.success(request, f"Set {target.username}'s balance to ${amt}.")
        else:
            messages.error(request, "Unknown action.")
        return redirect("accounts:manager_manage_balance", pk=pk)

    return render(request, "accounts/manage_balance.html", {"target": target, "profile": profile})


@login_required
def add_funds(request):
    user = request.user
    if not user.is_client:
        messages.error(request, "Only clients can add funds to a balance.")
        return redirect("core:dashboard")

    profile, _ = ClientProfile.objects.get_or_create(user=user)

    if request.method == "POST":
        form = AddFundsForm(request.POST)
        if form.is_valid():
            amt = form.cleaned_data["amount"]
            payment_method = form.cleaned_data.get("payment_method", "PAYSTACK")
            reference = form.cleaned_data.get("reference", "")

            if payment_method in ("PAYSTACK", "CARD", "MPESA"):
                email = request.user.email or f"{request.user.username}@datahire.test"
                try:
                    ref = reference or f"DEPOSIT-{request.user.id}-{int(time.time())}"
                    DepositTransaction.objects.create(
                        client=profile,
                        amount=amt,
                        status="PENDING",
                        payment_method=payment_method,
                        reference=ref
                    )
                    callback_url = request.build_absolute_uri(reverse("orders:paystack_callback"))
                    data = PaystackAPI.initialize_payment(
                        amount=amt,
                        email=email,
                        reference=ref,
                        client_profile=profile,
                        callback_url=callback_url
                    )
                    auth_url = data.get("authorization_url")
                    if auth_url:
                        return redirect(auth_url)
                    messages.error(request, "Failed to initialize Paystack payment (no authorization URL returned).")
                    return render(request, "accounts/add_funds.html", {"form": form, "profile": profile})
                except PaystackError as e:
                    messages.error(request, f"Paystack initialization failed: {e}")
                    return render(request, "accounts/add_funds.html", {"form": form, "profile": profile})
                except Exception as e:
                    messages.error(request, f"Payment error: {e}")
                    return render(request, "accounts/add_funds.html", {"form": form, "profile": profile})
            else:
                # Other external payment methods (e.g. PayPal)
                tx_ref = reference or f"EXT-{int(time.time())}"
                DepositTransaction.objects.create(
                    client=profile,
                    amount=amt,
                    status="COMPLETED",
                    payment_method=payment_method,
                    reference=tx_ref
                )
                profile.balance = (profile.balance or Decimal("0")) + amt
                profile.save(update_fields=["balance"])
                messages.success(request, f"Added ${amt} to your balance via {payment_method}.")
                return redirect("accounts:edit_profile")
    else:
        form = AddFundsForm()

    return render(request, "accounts/add_funds.html", {"form": form, "profile": profile})


@csrf_protect
def admin_login(request):
    """Simple admin login that accepts manager/staff users via email and redirects to Django admin."""
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        user = authenticate(request, username=email, password=password)
        if user is not None and (user.is_staff or user.is_manager or user.is_superuser):
            if user.is_suspended:
                messages.error(request, "This account is suspended.")
                return redirect("accounts:admin_login")
            login(request, user)
            messages.success(request, f"Welcome to admin, {user.get_full_name() or user.username}.")
            return redirect("/admin/")
        messages.error(request, "Invalid credentials or not allowed to access admin.")
    return render(request, "accounts/admin_login.html")

