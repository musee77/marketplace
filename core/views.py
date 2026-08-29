from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404

from services.models import Service, Category
from orders.models import Order
from accounts.models import User, SpecialistProfile, ClientProfile
from chat.models import Message
from reviews.models import Review
from blog.models import BlogPost


def home(request):
    from .models import SearchKeyword
    featured = (
        Service.objects
        .filter(
            is_active=True,
            specialist__specialist_profile__is_approved=True,
        )
        .select_related("specialist", "category")[:6]
    )
    listings = (
        Service.objects
        .filter(
            is_active=True,
            specialist__specialist_profile__is_approved=True,
        )
        .select_related("specialist", "category")
    )
    categories = Category.objects.all()
    top_reviews = (
        Review.objects.select_related("service", "reviewer", "reviewee")
        .order_by("-rating", "-created_at")[:10]
    )
    keywords = SearchKeyword.objects.filter(is_active=True)
    recent_order_activity = (
        Order.objects.filter(is_paid=True, service__isnull=False)
        .select_related("service", "service__category")
        .order_by("-created_at")[:6]
    )
    client_orders = Order.objects.none()
    if request.user.is_authenticated and request.user.is_client:
        client_orders = Order.objects.filter(client=request.user).select_related("service", "specialist")[:5]
    return render(
        request,
        "core/home.html",
        {
            "featured": featured,
            "listings": listings,
            "categories": categories,
            "top_reviews": top_reviews,
            "keywords": keywords,
            "recent_order_activity": recent_order_activity,
            "client_orders": client_orders,
        },
    )


def about(request):
    return render(request, "core/about.html")


def contact(request):
    from django.contrib import messages
    from django.db.models import Q
    from .forms import ContactForm
    from .models import ContactMessage

    user_inquiries = ContactMessage.objects.none()
    if request.user.is_authenticated:
        user_inquiries = ContactMessage.objects.filter(
            Q(user=request.user) | Q(email__iexact=request.user.email)
        ).order_by("-created_at")
        # Mark unread responses as seen
        user_inquiries.filter(is_read_by_user=False).update(is_read_by_user=True)

    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            contact_msg = form.save(commit=False)
            if request.user.is_authenticated:
                contact_msg.user = request.user
            contact_msg.save()
            messages.success(
                request,
                "Thank you for contacting us! Your message has been received, and our support team will respond to you shortly.",
            )
            # Re-fetch inquiries after saving
            if request.user.is_authenticated:
                user_inquiries = ContactMessage.objects.filter(
                    Q(user=request.user) | Q(email__iexact=request.user.email)
                ).order_by("-created_at")
            return render(request, "core/contact.html", {
                "form": ContactForm(),
                "submitted": True,
                "user_inquiries": user_inquiries,
            })
    else:
        initial = {}
        if request.user.is_authenticated:
            initial["name"] = request.user.get_full_name() or request.user.username
            initial["email"] = request.user.email
        form = ContactForm(initial=initial)

    return render(request, "core/contact.html", {
        "form": form,
        "submitted": False,
        "user_inquiries": user_inquiries,
    })



@login_required
def dashboard(request):
    user = request.user
    context = {}
    status = request.GET.get("status", "")
    if user.is_client:
        from orders.models import Offer
        client_orders = Order.objects.filter(client=user)
        client_profile, _ = ClientProfile.objects.get_or_create(user=user)
        context["client_balance"] = client_profile.balance
        context["client_total_orders"] = client_orders.count()
        context["client_completed_orders"] = client_orders.filter(status=Order.Status.COMPLETED).count()
        context["client_specialists_hired"] = client_orders.values("specialist").distinct().count()
        context["client_pending_offers"] = Offer.objects.filter(client=user, status=Offer.Status.PENDING).select_related("specialist")[:5]
        context["recent_blog_posts"] = (
            BlogPost.objects.published()
            .select_related("category")
            .order_by("-published_at", "-created_at")[:3]
        )
        orders = client_orders
    elif user.is_specialist:
        orders = Order.objects.filter(specialist=user)
        sp_profile, _ = SpecialistProfile.objects.get_or_create(user=user)
        context["specialist_balance"] = sp_profile.balance
        context["services"] = Service.objects.filter(specialist=user)
        context["specialist_completed_orders"] = orders.filter(status=Order.Status.COMPLETED).count()
        context["specialist_clients_worked_for"] = orders.values("client").distinct().count()
        context["pending_count"] = Order.objects.filter(specialist=user, status=Order.Status.PENDING).count()
        context["pending_orders"] = (
            Order.objects.filter(specialist=user, status=Order.Status.PENDING)
            .select_related("service", "client")[:10]
        )
    elif user.is_manager:
        context["total_users"] = User.objects.count()
        context["total_clients"] = User.objects.filter(role=User.Role.CLIENT).count()
        context["total_specialists"] = User.objects.filter(role=User.Role.SPECIALIST).count()
        context["unverified_specialists"] = SpecialistProfile.objects.filter(is_verified=False).count()
        context["pending_approvals"] = SpecialistProfile.objects.filter(is_approved=False).count()
        context["pending_messages"] = Message.objects.filter(is_approved=False, is_rejected=False).count()
        context["pending_specialists_list"] = SpecialistProfile.objects.filter(is_approved=False).select_related("user")[:6]
        context["pending_messages_list"] = Message.objects.filter(is_approved=False, is_rejected=False).select_related("sender", "conversation")[:6]
        context["total_orders"] = Order.objects.count()
        orders = Order.objects.all()
    else:
        orders = Order.objects.none()

    statuses_with_counts = []
    for value, label in Order.Status.choices:
        count = orders.filter(status=value).count()
        statuses_with_counts.append((value, label, count))

    if status:
        orders = orders.filter(status=status)

    orders_qs = orders.select_related("service", "client", "specialist")
    paginator = Paginator(orders_qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    context["orders"] = page_obj
    context["page_obj"] = page_obj
    context["status"] = status
    context["statuses"] = statuses_with_counts
    context["total_count"] = orders.count()
    context["services_for_modal"] = (
        Service.objects
        .filter(
            is_active=True,
            specialist__specialist_profile__is_approved=True,
        )
        .select_related("specialist")[:50]
    )
    if user.is_manager:
        context["recent_orders"] = orders[:10]
    return render(request, "core/dashboard.html", context)


@login_required
def my_inquiries(request):
    from django.contrib import messages
    from django.db.models import Q
    from .forms import ContactForm
    from .models import ContactMessage

    user = request.user

    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            contact_msg = form.save(commit=False)
            contact_msg.user = user
            contact_msg.save()
            messages.success(
                request,
                "Your inquiry has been submitted successfully! Our support team will review and respond here shortly.",
            )
            return redirect("core:my_inquiries")
    else:
        initial = {
            "name": user.get_full_name() or user.username,
            "email": user.email,
        }
        form = ContactForm(initial=initial)

    inquiries_qs = ContactMessage.objects.filter(
        Q(user=user) | Q(email__iexact=user.email)
    ).order_by("-created_at")

    # Mark all unread responses as read when viewing this page
    inquiries_qs.filter(is_read_by_user=False).update(is_read_by_user=True)

    paginator = Paginator(inquiries_qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "core/my_inquiries.html", {
        "form": form,
        "inquiries": page_obj,
        "page_obj": page_obj,
    })


@login_required
def inquiry_detail(request, pk):
    from django.http import Http404
    from .models import ContactMessage

    user = request.user
    inquiry = get_object_or_404(ContactMessage, pk=pk)

    # Security check: owner or manager only
    if not (inquiry.user == user or inquiry.email.lower() == user.email.lower() or user.is_manager):
        raise Http404("Inquiry not found.")

    if not inquiry.is_read_by_user and (inquiry.user == user or inquiry.email.lower() == user.email.lower()):
        inquiry.is_read_by_user = True
        inquiry.save(update_fields=["is_read_by_user"])

    return render(request, "core/inquiry_detail.html", {"inquiry": inquiry})



