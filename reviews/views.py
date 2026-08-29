from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden

from orders.models import Order
from .forms import ReviewForm


@login_required
def review_create(request, order_pk):
    order = get_object_or_404(Order, pk=order_pk)
    if request.user != order.client:
        return HttpResponseForbidden("Only the client can review this order.")
    if not order.is_reviewable:
        messages.error(request, "This order can't be reviewed right now.")
        return redirect(order.get_absolute_url())

    form = ReviewForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        review = form.save(commit=False)
        review.order = order
        review.service = order.service
        review.reviewer = request.user
        review.reviewee = order.specialist
        review.save()
        messages.success(request, "Thanks for your review!")
        return redirect(order.get_absolute_url())
    return render(request, "reviews/review_form.html", {"form": form, "order": order})
