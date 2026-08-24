from django.contrib import messages
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden, FileResponse
from django.urls import reverse
from django.conf import settings as django_settings

from services.models import Service
from .models import Order, Offer, OrderDocument
from .forms import OrderCreateForm, OfferCreateForm, OfferMessageForm, OrderDocumentForm, DeliverOrderForm, RequestRevisionForm
from django.utils import timezone
from decimal import Decimal
from accounts.models import ClientProfile, SpecialistProfile, User
from .paystack_api import PaystackAPI, PaystackError
from chat.models import Conversation, Message
import time


def is_client(user):
    return user.is_authenticated and user.is_client


def _save_order_attachments(order, uploaded_files, user):
    for uploaded_file in uploaded_files:
        title = uploaded_file.name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        OrderDocument.objects.create(
            order=order,
            title=title,
            file=uploaded_file,
            uploaded_by=user,
        )


@user_passes_test(is_client)
def order_create(request, slug):
    service = get_object_or_404(Service, slug=slug, is_active=True)
    form = OrderCreateForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        order = form.save(commit=False)
        # service is provided by URL in this flow, prefer that value
        order.service = service
        order.client = request.user
        order.specialist = service.specialist
        order.price = service.price
        attachments = form.cleaned_data.get("attachments", [])
        # handle payment: support BALANCE deduction or CARD payment redirect
        pm = form.cleaned_data.get("payment_method", Order.PAYMENT_METHODS[0][0])
        order.payment_method = pm
        if pm == 'BALANCE':
            profile, _ = ClientProfile.objects.get_or_create(user=request.user)
            if (profile.balance or Decimal('0')) >= order.price:
                profile.balance = (profile.balance or Decimal('0')) - order.price
                profile.save(update_fields=["balance"])
                order.compute_fees()
                order.is_paid = True
                order.paid_at = timezone.now()
                order.save()
                _save_order_attachments(order, attachments, request.user)
                order.credit_referral_reward()
            else:
                messages.error(request, "Insufficient balance. Please choose another payment method or top up your account.")
                return redirect(service.get_absolute_url())
        else:
            order.compute_fees()
            order.is_paid = False
            order.save()
            _save_order_attachments(order, attachments, request.user)

        if not order.is_paid:
            return redirect("orders:pay", pk=order.pk)

        messages.success(request, "Order placed! The specialist has been notified.")
        return redirect(order.get_absolute_url())
    return render(request, "orders/order_form.html", {"form": form, "service": service})


@user_passes_test(is_client)
def order_create_quick(request):
    """Create an order from a general form where the client selects a listing from a dropdown."""
    form = OrderCreateForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        order = form.save(commit=False)
        service = order.service
        order.client = request.user
        order.specialist = service.specialist
        order.price = service.price
        attachments = form.cleaned_data.get("attachments", [])
        pm = form.cleaned_data.get("payment_method", Order.PAYMENT_METHODS[0][0])
        order.payment_method = pm
        if pm == 'BALANCE':
            profile, _ = ClientProfile.objects.get_or_create(user=request.user)
            if (profile.balance or Decimal('0')) >= order.price:
                profile.balance = (profile.balance or Decimal('0')) - order.price
                profile.save(update_fields=["balance"])
                order.compute_fees()
                order.is_paid = True
                order.paid_at = timezone.now()
                order.save()
                _save_order_attachments(order, attachments, request.user)
                order.credit_referral_reward()
            else:
                messages.error(request, "Insufficient balance. Please choose another payment method or top up your account.")
                return redirect('orders:create_quick')
        else:
            order.compute_fees()
            order.is_paid = False
            order.save()
            _save_order_attachments(order, attachments, request.user)

        if not order.is_paid:
            return redirect("orders:pay", pk=order.pk)

        messages.success(request, "Order placed! The specialist has been notified.")
        return redirect(order.get_absolute_url())
    return render(request, "orders/order_form_quick.html", {"form": form})


@login_required
def order_list(request):
    query_string = request.META.get("QUERY_STRING", "")
    destination = reverse("core:dashboard")
    if query_string:
        destination = f"{destination}?{query_string}"
    return redirect(destination)


@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order.objects.select_related("service", "client", "specialist"), pk=pk)
    user = request.user
    if user not in (order.client, order.specialist) and not user.is_manager:
        return HttpResponseForbidden("You don't have access to this order.")

    # Specialist cannot view unpaid orders
    if user == order.specialist and not order.is_paid:
        return HttpResponseForbidden("This order has not been paid for yet.")

    allowed_next = []
    if user == order.specialist:
        allowed_next = order.SPECIALIST_ACTIONS.get(order.status, [])
    elif user == order.client:
        allowed_next = order.CLIENT_ACTIONS.get(order.status, [])

    # Remove DELIVERED from the sidebar action buttons — specialist uses the
    # inline delivery form that enforces document upload.
    allowed_next_filtered = [s for s in allowed_next if s != Order.Status.DELIVERED]

    document_form = OrderDocumentForm()
    deliver_form = DeliverOrderForm()
    revision_form = RequestRevisionForm()
    documents = order.documents.select_related("uploaded_by")
    # Separate delivery documents (uploaded by specialist) from client reference docs
    delivery_docs = documents.filter(uploaded_by=order.specialist)
    client_docs = documents.filter(uploaded_by=order.client)

    # ── Inline delivery POST (specialist submits delivery form on this page) ──
    if request.method == "POST" and user == order.specialist and "deliver_submit" in request.POST:
        if order.status not in (Order.Status.IN_PROGRESS, Order.Status.UNDER_REVISION):
            messages.error(request, f"Work can only be delivered when In Progress or Under Revision (currently: {order.get_status_display()}).")
            return redirect(order.get_absolute_url())
        deliver_form = DeliverOrderForm(request.POST, request.FILES)
        if deliver_form.is_valid():
            delivery_note = deliver_form.cleaned_data.get("delivery_note", "")
            uploaded_files = deliver_form.cleaned_data["files"]
            for f in uploaded_files:
                title = f.name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
                OrderDocument.objects.create(order=order, title=title, file=f, uploaded_by=user)
            if delivery_note:
                order.delivery_note = delivery_note
            order.status = Order.Status.DELIVERED
            order.save(update_fields=["status", "delivery_note", "updated_at"])
            messages.success(request, "Work delivered! The client has been notified and can now download your files.")
            return redirect(order.get_absolute_url())
        # fall through to render with form errors

    can_deliver = Order.Status.DELIVERED in order.SPECIALIST_ACTIONS.get(order.status, []) and user == order.specialist
    can_request_revision = (
        user == order.client and order.status == Order.Status.DELIVERED and order.is_paid
    )

    return render(request, "orders/order_detail.html", {
        "order": order,
        "allowed_next": allowed_next_filtered,
        "can_deliver": can_deliver,
        "can_request_revision": can_request_revision,
        "documents": documents,
        "delivery_docs": delivery_docs,
        "client_docs": client_docs,
        "document_form": document_form,
        "deliver_form": deliver_form,
        "revision_form": revision_form,
    })


@login_required
def order_document_upload(request, pk):
    """Allow the client assigned to an order to upload reference documents."""
    order = get_object_or_404(Order, pk=pk)
    if request.user != order.client:
        return HttpResponseForbidden("Only the client can upload reference documents here.")
    if request.method != "POST":
        return redirect(order.get_absolute_url())
    form = OrderDocumentForm(request.POST, request.FILES)
    if form.is_valid():
        document = form.save(commit=False)
        document.order = order
        document.uploaded_by = request.user
        document.save()
        messages.success(request, "Document uploaded to the order.")
    else:
        for error in form.errors.values():
            messages.error(request, error)
    return redirect(order.get_absolute_url())


@login_required
def order_deliver(request, pk):
    """
    Specialist delivers work: must upload at least one file.
    Marks the order as DELIVERED atomically with the document upload.
    """
    order = get_object_or_404(Order.objects.select_related("client", "specialist"), pk=pk)

    if request.user != order.specialist:
        return HttpResponseForbidden("Only the specialist assigned to this order can deliver work.")

    if not order.is_paid:
        return HttpResponseForbidden("This order has not been paid for yet.")

    if order.status not in (Order.Status.IN_PROGRESS, Order.Status.UNDER_REVISION):
        messages.error(request, f"Work can only be delivered when the order is In Progress or Under Revision (currently: {order.get_status_display()}).")
        return redirect(order.get_absolute_url())

    form = DeliverOrderForm(request.POST or None, request.FILES or None)

    if request.method == "POST":
        if form.is_valid():
            delivery_note = form.cleaned_data.get("delivery_note", "")
            uploaded_files = form.cleaned_data["files"]

            # Save each delivery file as an OrderDocument
            for f in uploaded_files:
                title = f.name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
                OrderDocument.objects.create(
                    order=order,
                    title=title,
                    file=f,
                    uploaded_by=request.user,
                )

            if delivery_note:
                order.delivery_note = delivery_note

            # Mark order as DELIVERED
            order.status = Order.Status.DELIVERED
            order.save(update_fields=["status", "delivery_note", "updated_at"])

            messages.success(request, "Work delivered! The client has been notified and can now download your files.")
            return redirect(order.get_absolute_url())

    return render(request, "orders/order_deliver.html", {
        "order": order,
        "form": form,
    })


@login_required
def order_document_download(request, pk):
    """Serve an order document only to the client, specialist, or manager."""
    document = get_object_or_404(OrderDocument.objects.select_related("order"), pk=pk)
    order = document.order
    if request.user not in (order.client, order.specialist) and not request.user.is_manager:
        return HttpResponseForbidden("You don't have access to this document.")
    document.file.open("rb")
    filename = document.file.name.rsplit("/", 1)[-1]
    return FileResponse(document.file, as_attachment=True, filename=filename)


@user_passes_test(is_client)
def order_cancel(request, pk):
    order = get_object_or_404(Order.objects.select_related("service", "specialist"), pk=pk, client=request.user)

    if order.status != Order.Status.PENDING:
        messages.error(request, "Only pending orders can be cancelled.")
        return redirect(order.get_absolute_url())

    if request.method == "POST":
        order.status = Order.Status.CANCELLED
        order.save(update_fields=["status", "updated_at"])
        messages.success(request, f"Order #{order.pk} has been cancelled.")
        return redirect(order.get_absolute_url())

    return render(request, "orders/order_cancel.html", {"order": order})


@login_required
def order_decide(request, pk):
    order = get_object_or_404(Order.objects.select_related("service", "client", "specialist"), pk=pk)
    user = request.user

    if user != order.specialist:
        return HttpResponseForbidden("You don't have access to this order.")

    if not order.is_paid:
        return HttpResponseForbidden("This order has not been paid for yet.")

    if order.status != Order.Status.PENDING:
        messages.info(request, f"Order #{order.pk} is already {order.get_status_display().lower()}.")
        return redirect(order.get_absolute_url())

    return render(request, "orders/order_decide.html", {"order": order})


@user_passes_test(is_client)
def order_pay(request, pk):
    order = get_object_or_404(Order, pk=pk, client=request.user)

    if order.is_paid:
        messages.info(request, "This order is already paid.")
        return redirect(order.get_absolute_url())

    if request.method == "POST":
        # Allow the client to change/select the payment method on this page
        selected_pm = request.POST.get("payment_method")
        if selected_pm in dict(Order.PAYMENT_METHODS):
            order.payment_method = selected_pm
            order.save(update_fields=["payment_method"])

        if order.payment_method == "MPESA":
            order.payment_method = "CARD"
            order.save(update_fields=["payment_method"])
            messages.error(request, "M-Pesa is no longer available. Please choose card or account balance.")
            return render(request, "orders/order_pay.html", {"order": order, "payment_methods": Order.PAYMENT_METHODS})

        # Balance payment
        if order.payment_method == 'BALANCE':
            profile, _ = ClientProfile.objects.get_or_create(user=request.user)
            if (profile.balance or Decimal('0')) >= order.price:
                profile.balance = (profile.balance or Decimal('0')) - order.price
                profile.save(update_fields=["balance"])
                order.compute_fees()
                order.is_paid = True
                order.paid_at = timezone.now()
                order.save(update_fields=["is_paid", "paid_at", "platform_fee", "platform_fee_rate", "referral_bonus", "specialist_earnings", "referrer"])
                order.credit_referral_reward()
                if order.offer_message_id:
                    from chat.models import Message as ChatMessage
                    ChatMessage.objects.filter(
                        pk=order.offer_message_id,
                        message_type="OFFER",
                        offer_status="PENDING",
                    ).update(offer_status="ACCEPTED")
                messages.success(request, "Payment received from account balance — thank you!")
                return redirect(order.get_absolute_url())
            else:
                messages.error(request, "Insufficient balance to complete payment.")
                return render(request, "orders/order_pay.html", {"order": order, "payment_methods": Order.PAYMENT_METHODS})

        elif order.payment_method == 'CARD':
            email = request.user.email or f"{request.user.username}@datahire.test"
            try:
                ref = f"ORDER-{order.pk}-{int(time.time())}"
                callback_url = request.build_absolute_uri(reverse('orders:paystack_callback'))
                data = PaystackAPI.initialize_payment(
                    amount=order.price,
                    email=email,
                    reference=ref,
                    client_profile=getattr(request.user, 'client_profile', None),
                    callback_url=callback_url
                )
                auth_url = data.get('authorization_url')
                if auth_url:
                    return redirect(auth_url)
                messages.error(request, "Failed to initialize Paystack payment (no authorization URL returned).")
                return render(request, "orders/order_pay.html", {"order": order, "payment_methods": Order.PAYMENT_METHODS})
            except PaystackError as e:
                messages.error(request, f"Paystack initialization failed: {e}")
                return render(request, "orders/order_pay.html", {"order": order, "payment_methods": Order.PAYMENT_METHODS})
            except Exception as e:
                messages.error(request, f"Payment error: {e}")
                return render(request, "orders/order_pay.html", {"order": order, "payment_methods": Order.PAYMENT_METHODS})

    return render(request, "orders/order_pay.html", {"order": order, "payment_methods": Order.PAYMENT_METHODS})


@login_required
def order_transition(request, pk, new_status):
    order = get_object_or_404(Order, pk=pk)
    if not order.is_paid:
        messages.error(request, "This order cannot be modified because it is not paid.")
        return redirect(order.get_absolute_url())

    user = request.user
    allowed = []
    if user == order.specialist:
        allowed = order.SPECIALIST_ACTIONS.get(order.status, [])
    elif user == order.client:
        allowed = order.CLIENT_ACTIONS.get(order.status, [])

    if new_status not in allowed:
        messages.error(request, "That action isn't allowed right now.")
        return redirect(order.get_absolute_url())

    order.status = new_status
    order.save(update_fields=["status", "updated_at"])

    # When client marks order COMPLETED, credit the specialist their earnings
    if new_status == Order.Status.COMPLETED:
        sp, _ = SpecialistProfile.objects.get_or_create(user=order.specialist)
        sp.balance = (sp.balance or Decimal('0')) + order.specialist_earnings
        sp.save(update_fields=["balance"])

    messages.success(request, f"Order marked as {order.get_status_display()}.")
    return redirect(order.get_absolute_url())


@login_required
@user_passes_test(is_client)
def order_request_revision(request, pk):
    """Client requests a revision on a delivered order. Requires written instructions."""
    order = get_object_or_404(Order.objects.select_related("client", "specialist"), pk=pk, client=request.user)

    if not order.is_paid:
        messages.error(request, "This order has not been paid for.")
        return redirect(order.get_absolute_url())

    if order.status != Order.Status.DELIVERED:
        messages.error(request, "Revisions can only be requested when the order has been delivered.")
        return redirect(order.get_absolute_url())

    if request.method == "POST":
        form = RequestRevisionForm(request.POST)
        if form.is_valid():
            order.revision_note = form.cleaned_data["instructions"]
            order.status = Order.Status.UNDER_REVISION
            order.save(update_fields=["revision_note", "status", "updated_at"])
            messages.success(request, "Revision requested. The specialist has been notified of your instructions.")
            return redirect(order.get_absolute_url())
        else:
            # Re-render order detail with revision form errors
            messages.error(request, "Please describe what you'd like the specialist to change.")
            return redirect(order.get_absolute_url())

    # GET requests just redirect back — the form is inline on order_detail
    return redirect(order.get_absolute_url())


def paystack_callback(request):
    """A simple callback endpoint that Paystack can redirect to with `reference`.

    This view verifies the reference with Paystack and updates either an Order
    (reference starting with 'ORDER-<pk>-...') or a DepositTransaction
    (reference starting with 'DEPOSIT-<user_id>-...' or exact match).
    """
    reference = request.GET.get('reference') or request.POST.get('reference')
    if not reference:
        messages.error(request, "Missing payment reference.")
        return redirect('core:dashboard')

    try:
        data = PaystackAPI.verify_payment(reference)
    except PaystackError as e:
        messages.error(request, f"Payment verification failed: {e}")
        return redirect('core:dashboard')

    status = data.get('status')
    # Paystack returns 'success' for completed transactions
    if status != 'success' and data.get('gateway_response') != 'Successful':
        messages.error(request, f"Payment not successful: {data.get('gateway_response')}")
        return redirect('core:dashboard')

    # Handle ORDER-<pk>-... references
    if reference.startswith('ORDER-'):
        # expected format ORDER-<pk>-<ts>
        parts = reference.split('-')
        if len(parts) >= 2:
            try:
                pk = int(parts[1])
                order = Order.objects.get(pk=pk)
                if not order.is_paid:
                    order.compute_fees()
                    order.is_paid = True
                    order.paid_at = timezone.now()
                    order.save(update_fields=["is_paid", "paid_at", "platform_fee", "platform_fee_rate", "referral_bonus", "specialist_earnings", "referrer"])
                    order.credit_referral_reward()
                    
                    # If this order was created from an offer, now mark the offer ACCEPTED
                    if order.offer_message_id:
                        try:
                            from chat.models import Message as ChatMessage
                            offer_msg = ChatMessage.objects.get(pk=order.offer_message_id, message_type="OFFER")
                            if offer_msg.offer_status == "PENDING":
                                offer_msg.offer_status = "ACCEPTED"
                                offer_msg.save(update_fields=["offer_status"])
                        except Exception:
                            pass  # Non-critical — order payment still succeeded
                    
                    messages.success(request, f"Payment received for Order #{order.pk}.")
                    return redirect(order.get_absolute_url())
                else:
                    messages.info(request, "Order already marked paid.")
                    return redirect(order.get_absolute_url())
            except Exception:
                messages.error(request, "Unable to locate order for payment reference.")
                return redirect('core:dashboard')

    # Handle DEPOSIT- references: find DepositTransaction and complete it
    if reference.startswith('DEPOSIT-') or True:
        try:
            from accounts.models import DepositTransaction
            tx = DepositTransaction.objects.filter(reference=reference).first()
            if tx and tx.status != 'COMPLETED':
                tx.status = 'COMPLETED'
                tx.save(update_fields=['status'])
                prof = tx.client
                prof.balance = (prof.balance or Decimal('0')) + tx.amount
                prof.save(update_fields=['balance'])
                messages.success(request, f"Deposit completed: ${tx.amount} added to your balance.")
                # Redirect to profile edit page or dashboard
                return redirect('accounts:edit_profile')
        except Exception:
            # fallthrough to generic redirect
            pass

    messages.info(request, "Payment verified.")
    return redirect('core:dashboard')


# ===== OFFER VIEWS (Specialist → Client) =====

def is_specialist(user):
    return user.is_authenticated and user.is_specialist


@login_required
@user_passes_test(is_specialist)
def offer_create(request, client_id):
    """Specialist sends an offer to a specific client via chat. Auto-approved, no admin review needed."""
    client = get_object_or_404(User, pk=client_id)
    
    # Verify client is actually a client and not suspended
    if client.role != User.Role.CLIENT:
        messages.error(request, "This user is not a client.")
        return redirect("chat:inbox")
    
    if client.is_suspended:
        messages.error(request, "This client is suspended and cannot receive offers.")
        return redirect("chat:inbox")
    
    form = OfferCreateForm(request.POST or None, specialist=request.user)
    if request.method == "POST" and form.is_valid():
        # Get or create conversation between specialist and client
        conversation, created = Conversation.objects.get_or_create_between(request.user, client)
        
        # Create offer as a Message with message_type="OFFER"
        offer_message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            message_type="OFFER",
            offer_title=form.cleaned_data["title"],
            offer_description=form.cleaned_data["description"],
            offer_price=form.cleaned_data["price"],
            offer_delivery_days=form.cleaned_data["delivery_days"],
            offer_service=form.cleaned_data["service"],
        )
        # save() method auto-approves offer messages
        
        messages.success(request, f"Offer sent to {client.get_full_name() or client.username}!")
        return redirect("chat:conversation", pk=conversation.pk)
    
    return render(request, "orders/offer_form.html", {
        "form": form,
        "client": client,
        "title": f"Send offer to {client.get_full_name() or client.username}",
    })


@login_required
@user_passes_test(is_specialist)
def offer_message_edit(request, pk):
    """Edit one of the current specialist's pending chat offers."""
    offer_message = get_object_or_404(
        Message,
        pk=pk,
        sender=request.user,
        message_type="OFFER",
    )
    if offer_message.offer_status != "PENDING":
        messages.error(request, "Accepted or declined offers cannot be edited.")
        return redirect("chat:conversation", pk=offer_message.conversation_id)
    form = OfferMessageForm(request.POST or None, instance=offer_message, specialist=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Offer updated.")
        return redirect("chat:conversation", pk=offer_message.conversation_id)
    return render(request, "orders/offer_message_form.html", {
        "form": form,
        "offer_message": offer_message,
        "title": "Edit offer",
    })


@login_required
@user_passes_test(is_specialist)
def offer_message_delete(request, pk):
    """Delete one of the current specialist's pending chat offers."""
    offer_message = get_object_or_404(
        Message,
        pk=pk,
        sender=request.user,
        message_type="OFFER",
    )
    if offer_message.offer_status != "PENDING":
        messages.error(request, "Accepted or declined offers cannot be deleted.")
        return redirect("chat:conversation", pk=offer_message.conversation_id)
    conversation_id = offer_message.conversation_id
    if request.method == "POST":
        offer_message.delete()
        messages.success(request, "Offer deleted.")
        return redirect("chat:conversation", pk=conversation_id)
    return render(request, "orders/offer_message_confirm_delete.html", {
        "offer_message": offer_message,
    })


@login_required
@user_passes_test(is_specialist)
def offer_list_sent(request):
    """Specialist views all offers they've sent."""
    offers_qs = Offer.objects.filter(specialist=request.user).select_related("client").order_by("-created_at")
    pending_count = offers_qs.filter(status=Offer.Status.PENDING).count()
    paginator = Paginator(offers_qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    
    return render(request, "orders/offer_list_sent.html", {
        "offers": page_obj,
        "page_obj": page_obj,
        "pending_count": pending_count,
    })


@login_required
@user_passes_test(is_client)
def offer_list_received(request):
    """Client views all offers they've received from specialists. Auto-approved, no admin review."""
    offers_qs = Offer.objects.filter(client=request.user).select_related("specialist").order_by("-created_at")
    pending_count = offers_qs.filter(status=Offer.Status.PENDING).count()
    paginator = Paginator(offers_qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    
    return render(request, "orders/offer_list_received.html", {
        "offers": page_obj,
        "page_obj": page_obj,
        "pending_count": pending_count,
    })


@login_required
def offer_detail(request, pk):
    """View offer details. Specialist can edit pending offers, client can accept/decline."""
    offer = get_object_or_404(Offer, pk=pk)
    
    # Permission check
    is_specialist = request.user == offer.specialist
    is_client = request.user == offer.client
    
    if not (is_specialist or is_client):
        return HttpResponseForbidden("You don't have permission to view this offer.")
    
    context = {
        "offer": offer,
        "is_specialist": is_specialist,
        "is_client": is_client,
        "can_accept": is_client and offer.status == Offer.Status.PENDING,
        "can_decline": is_client and offer.status == Offer.Status.PENDING,
        "can_edit": is_specialist and offer.status == Offer.Status.PENDING,
    }
    
    return render(request, "orders/offer_detail.html", context)


@login_required
@user_passes_test(is_client)
def offer_accept(request, pk):
    """Client accepts an offer message. Creates an Order and redirects to payment.
    
    The offer status remains PENDING until payment is confirmed. It is only
    marked ACCEPTED inside paystack_callback once the payment succeeds.
    """
    offer_message = get_object_or_404(Message, pk=pk, message_type="OFFER")
    
    # Check if offer was already accepted/declined
    if offer_message.offer_status != "PENDING":
        messages.warning(request, f"This offer has already been {offer_message.offer_status.lower()}.")
        return redirect("chat:conversation", pk=offer_message.conversation.pk)
    
    # Verify the request user is the recipient of the offer
    other_participant = offer_message.conversation.other_participant(request.user)
    if other_participant != offer_message.sender:
        messages.error(request, "You don't have permission to accept this offer.")
        return redirect("chat:inbox")
    
    # Create an Order from the offer message
    try:
        order = Order(
            service=offer_message.offer_service,
            client=request.user,
            specialist=offer_message.sender,
            price=offer_message.offer_price,
            status=Order.Status.PENDING,
            requirements=offer_message.offer_description,
            due_date=timezone.now().date() + timezone.timedelta(days=offer_message.offer_delivery_days),
            payment_method="CARD",
            # Store offer message ID so the callback can mark it ACCEPTED after payment
            offer_message_id=offer_message.pk,
        )
        order.compute_fees()
        order.save()
        
        # NOTE: offer_status stays PENDING — it will be set to ACCEPTED only
        # after successful payment verification in paystack_callback.
        
        messages.success(request, "Offer accepted! Please complete payment to confirm.")
        return redirect('orders:pay', pk=order.pk)
    except Exception as e:
        messages.error(request, f"Error accepting offer: {e}")
        return redirect("chat:conversation", pk=offer_message.conversation.pk)


@login_required
@user_passes_test(is_client)
def offer_decline(request, pk):
    """Client declines an offer message. Requires an explicit POST (Reject button)."""
    offer_message = get_object_or_404(Message, pk=pk, message_type="OFFER")
    
    # Only allow via explicit POST (the Reject button)
    if request.method != "POST":
        messages.error(request, "Invalid request.")
        return redirect("chat:conversation", pk=offer_message.conversation.pk)
    
    # Check if offer was already accepted/declined
    if offer_message.offer_status != "PENDING":
        messages.warning(request, f"This offer has already been {offer_message.offer_status.lower()}.")
        return redirect("chat:conversation", pk=offer_message.conversation.pk)
    
    # Verify the request user is the recipient of the offer
    other_participant = offer_message.conversation.other_participant(request.user)
    if other_participant != offer_message.sender:
        messages.error(request, "You don't have permission to decline this offer.")
        return redirect("chat:inbox")
    
    # Mark offer as declined only when the client explicitly clicks Reject
    offer_message.offer_status = "DECLINED"
    offer_message.is_rejected = False
    offer_message.save(update_fields=["offer_status", "is_rejected"])
    
    messages.info(request, "Offer declined.")
    return redirect("chat:conversation", pk=offer_message.conversation.pk)
