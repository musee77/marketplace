from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Max, Count
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from accounts.models import User
from .models import Conversation, Message, SystemChatMessage
from .forms import MessageForm


def is_manager(user):
    return user.is_authenticated and user.is_manager


def system_chat_reply(question):
    normalized = question.lower()
    replies = (
        (("offer", "proposal"), "Open a conversation with a client, then choose Send Offer. Clients can accept or decline it in the chat."),
        (("pay", "payment", "paystack", "card"), "Accepted orders take you to the payment page. Card payments use Paystack; account balance is also available when funded."),
        (("order", "work"), "Your orders are available from the Dashboard. Open an order to view payment, status, requirements, and delivery details."),
        (("specialist", "analyst", "service"), "Use Browse analysts to compare specialists and their services, then open a profile to get started."),
        (("help", "support", "contact"), "I can help with offers, payments, orders, and finding specialists. For account issues, use the profile or contact support."),
    )
    for keywords, reply in replies:
        if any(keyword in normalized for keyword in keywords):
            return reply
    return "I can help with offers, payments, orders, and finding specialists. Try asking about one of those."


@login_required
@require_http_methods(["GET", "POST"])
def system_chat(request):
    """Return or append the authenticated user's persisted assistant conversation."""
    if request.method == "GET":
        messages_qs = SystemChatMessage.objects.filter(user=request.user).order_by("-created_at")[:40]
        messages_qs = reversed(list(messages_qs))
        return JsonResponse({"messages": [
            {"role": message.role.lower(), "body": message.body}
            for message in messages_qs
        ]})

    question = (request.POST.get("question") or "").strip()
    if not question:
        return JsonResponse({"error": "Ask a question first."}, status=400)
    if len(question) > 240:
        return JsonResponse({"error": "Questions must be 240 characters or fewer."}, status=400)

    answer = system_chat_reply(question)
    SystemChatMessage.objects.bulk_create([
        SystemChatMessage(user=request.user, role="USER", body=question),
        SystemChatMessage(user=request.user, role="ASSISTANT", body=answer),
    ])
    return JsonResponse({"messages": [
        {"role": "user", "body": question},
        {"role": "assistant", "body": answer},
    ]})


@login_required
def inbox(request):
    conversations_qs = (
        Conversation.objects
        .filter(participants=request.user)
        .annotate(last_msg_time=Max("messages__created_at"))
        .order_by("-last_msg_time")
    )

    # Show only conversations with the opposite role:
    #   - Specialist → only conversations with clients
    #   - Client     → only conversations with specialists
    if request.user.is_specialist:
        # Get all other specialists (not the current user)
        other_specialists = User.objects.filter(role=User.Role.SPECIALIST).exclude(pk=request.user.pk)
        # Exclude any conversation that contains another specialist
        conversations_qs = conversations_qs.exclude(participants__in=other_specialists)
    elif request.user.is_client:
        # Get all other clients (not the current user)
        other_clients = User.objects.filter(role=User.Role.CLIENT).exclude(pk=request.user.pk)
        # Exclude any conversation that contains another client
        conversations_qs = conversations_qs.exclude(participants__in=other_clients)

    # Paginate the queryset — 10 per page
    paginator = Paginator(conversations_qs, 10)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    # Enrich only the current page's conversations
    conv_list = []
    for c in page_obj.object_list:
        other = c.other_participant(request.user)
        if not other:
            continue
        last = c.last_visible_message_for(request.user)
        pending_count = c.messages.filter(is_approved=False, is_rejected=False).exclude(sender=request.user).count()
        unread_count = c.messages.filter(is_approved=True, is_read=False).exclude(sender=request.user).count()
        conv_list.append({"conversation": c, "other": other, "last": last, "pending": pending_count, "unread": unread_count})

    if request.user.is_client:
        quick_contacts = (
            User.objects.filter(role=User.Role.SPECIALIST, is_suspended=False)
            .select_related("specialist_profile")
            .order_by("-date_created")[:6]
        )
        quick_label = "Message specialist"
        from orders.models import Offer
        pending_offers = Offer.objects.filter(client=request.user, status=Offer.Status.PENDING).select_related("specialist").order_by("-created_at")
    elif request.user.is_specialist:
        quick_contacts = User.objects.filter(role=User.Role.CLIENT, is_suspended=False).order_by("-date_created")[:6]
        quick_label = "Message client"
        pending_offers = None
    else:
        quick_contacts = User.objects.none()
        quick_label = "Message user"
        pending_offers = None

    return render(request, "chat/inbox.html", {
        "conversations": conv_list,
        "page_obj": page_obj,
        "quick_contacts": quick_contacts,
        "quick_label": quick_label,
        "pending_offers": pending_offers,
    })


@login_required
def conversation_detail(request, pk):
    conversation = get_object_or_404(Conversation, pk=pk)
    if not conversation.participants.filter(pk=request.user.pk).exists():
        messages.error(request, "You are not part of this conversation.")
        return redirect("chat:inbox")

    # Mark incoming messages as read
    conversation.messages.filter(is_approved=True, is_read=False).exclude(sender=request.user).update(is_read=True)

    # Show approved messages + user's own pending messages + offers (exclude only moderator-rejected text messages)
    my_messages = Q(sender=request.user)
    approved = Q(is_approved=True)
    is_offer = Q(message_type="OFFER")
    rejected_text = Q(is_rejected=True, message_type="TEXT")
    visible_messages = conversation.messages.filter(my_messages | approved | is_offer).exclude(rejected_text)

    form = MessageForm()
    if request.method == "POST":
        form = MessageForm(request.POST, request.FILES)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.conversation = conversation
            msg.sender = request.user
            # Handle optional file attachment
            attachment = form.cleaned_data.get("attachment")
            if attachment:
                msg.attachment = attachment
                msg.attachment_name = attachment.name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
            msg.save()
            # Update conversation timestamp
            conversation.save()
            if request.user.role == User.Role.SPECIALIST:
                messages.info(request, "Message sent. It will be visible after admin approval.")
            else:
                messages.success(request, "Message sent.")
            return redirect("chat:conversation", pk=conversation.pk)

    other = conversation.other_participant(request.user)
    return render(request, "chat/conversation.html", {
        "conversation": conversation,
        "chat_messages": visible_messages,
        "form": form,
        "other": other,
    })


@login_required
def chat_attachment_download(request, pk):
    """Serve a chat message attachment only to conversation participants."""
    from django.http import FileResponse, HttpResponseForbidden
    msg = get_object_or_404(Message, pk=pk)
    if not msg.attachment:
        from django.http import Http404
        raise Http404("No attachment on this message.")
    if not msg.conversation.participants.filter(pk=request.user.pk).exists():
        return HttpResponseForbidden("You don't have access to this file.")
    msg.attachment.open("rb")
    filename = msg.attachment_name or msg.attachment.name.rsplit("/", 1)[-1]
    return FileResponse(msg.attachment, as_attachment=True, filename=filename)


@login_required
def start_conversation(request, user_id):
    """Start or resume a conversation with another user."""
    other_user = get_object_or_404(User, pk=user_id)
    if other_user == request.user:
        messages.error(request, "You cannot message yourself.")
        return redirect("chat:inbox")

    # Check if conversation already exists between these two users
    existing = Conversation.objects.filter(participants=request.user).filter(participants=other_user).first()
    if existing:
        return redirect("chat:conversation", pk=existing.pk)

    # Create new conversation
    conversation = Conversation.objects.create()
    conversation.participants.add(request.user, other_user)
    messages.success(request, f"Conversation started with {other_user.get_full_name() or other_user.username}.")
    return redirect("chat:conversation", pk=conversation.pk)


# ── Manager moderation ──────────────────────────────────────────

@user_passes_test(is_manager)
def moderate_messages(request):
    pending = (
        Message.objects
        .filter(is_approved=False, is_rejected=False)
        .select_related("sender", "conversation")
        .order_by("-created_at")
    )
    return render(request, "chat/moderate.html", {"pending_messages": pending})


@user_passes_test(is_manager)
def approve_message(request, pk):
    msg = get_object_or_404(Message, pk=pk)
    msg.is_approved = True
    msg.is_rejected = False
    msg.save(update_fields=["is_approved", "is_rejected"])
    messages.success(request, "Message approved.")
    return redirect(request.META.get("HTTP_REFERER") or "chat:moderate")


@user_passes_test(is_manager)
def reject_message(request, pk):
    msg = get_object_or_404(Message, pk=pk)
    msg.is_rejected = True
    msg.is_approved = False
    msg.save(update_fields=["is_approved", "is_rejected"])
    messages.success(request, "Message rejected.")
    return redirect(request.META.get("HTTP_REFERER") or "chat:moderate")
