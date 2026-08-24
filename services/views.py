from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q

from .models import Service, Category
from .forms import ServiceForm
from orders.forms import OrderCreateForm
from django import forms as django_forms


def service_list(request):
    services = (
        Service.objects
        .filter(
            is_active=True,
            specialist__specialist_profile__is_approved=True,
        )
        .select_related("specialist", "category")
    )
    q = request.GET.get("q", "")
    category_slug = request.GET.get("category", "")
    current_category = None
    if q:
        services = services.filter(Q(title__icontains=q) | Q(description__icontains=q) | Q(specialist__username__icontains=q))
    if category_slug:
        services = services.filter(category__slug=category_slug)
        current_category = Category.objects.filter(slug=category_slug).first()

    paginator = Paginator(services, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "services/service_list.html", {
        "page_obj": page_obj,
        "categories": Category.objects.all(),
        "q": q,
        "category_slug": category_slug,
        "current_category": current_category,
    })


def service_detail(request, slug):
    qs = Service.objects.select_related("specialist__specialist_profile", "category")
    service = get_object_or_404(qs, slug=slug)

    # Owner can always preview their own listing (regardless of approval/active status)
    is_owner = request.user.is_authenticated and service.specialist == request.user
    if not is_owner:
        # For everyone else: must be active and specialist must be approved
        if not service.is_active or not hasattr(service.specialist, "specialist_profile") or not service.specialist.specialist_profile.is_approved:
            from django.http import Http404
            raise Http404

    reviews = service.reviews.select_related("reviewer")
    order_form = None
    if request.user.is_authenticated and request.user.is_client:
        order_form = OrderCreateForm(initial={"service": service})
        try:
            order_form.fields["service"].widget = django_forms.HiddenInput()
        except Exception:
            pass
    return render(request, "services/service_detail.html", {
        "service": service,
        "reviews": reviews,
        "order_form": order_form,
        "is_owner": is_owner,
    })


def is_specialist(user):
    return user.is_authenticated and user.is_specialist


@user_passes_test(is_specialist)
def service_create(request):
    form = ServiceForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        service = form.save(commit=False)
        service.specialist = request.user
        service.save()
        messages.success(request, "Service listing published. It will appear publicly once your profile is approved.")
        return redirect("services:mine")
    return render(request, "services/service_form.html", {"form": form, "is_new": True})


@user_passes_test(is_specialist)
def service_edit(request, slug):
    service = get_object_or_404(Service, slug=slug, specialist=request.user)
    form = ServiceForm(request.POST or None, request.FILES or None, instance=service)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Service updated.")
        return redirect("services:mine")
    return render(request, "services/service_form.html", {"form": form, "is_new": False, "service": service})


@user_passes_test(is_specialist)
def service_delete(request, slug):
    service = get_object_or_404(Service, slug=slug, specialist=request.user)
    if request.method == "POST":
        service.delete()
        messages.success(request, "Service removed.")
        return redirect("core:dashboard")
    return render(request, "services/service_confirm_delete.html", {"service": service})


@user_passes_test(is_specialist)
def my_services(request):
    services = Service.objects.filter(specialist=request.user)
    paginator = Paginator(services, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    reviews = request.user.reviews_received.select_related("reviewer", "service").order_by("-created_at")
    reviews_paginator = Paginator(reviews, 5)
    reviews_page = reviews_paginator.get_page(request.GET.get("reviews_page"))
    return render(request, "services/my_services.html", {
        "services": page_obj,
        "page_obj": page_obj,
        "reviews_page": reviews_page,
    })
