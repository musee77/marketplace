from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum, Q
from django.utils import timezone
from django.utils.text import slugify
from decimal import Decimal

from accounts.models import User, SpecialistProfile, ClientProfile
from services.models import Category, Service
from orders.models import Order, OrderDocument
from orders.forms import OrderDocumentForm
from chat.models import Message
from reviews.models import Review
from blog.models import BlogCategory, BlogPost
from core.models import ContactMessage

from .forms import BlogPostForm, CategoryForm, UserForm, BalanceForm, AdminServiceForm


def is_manager(user):
    return user.is_authenticated and (user.is_manager or user.is_staff or user.is_superuser)


# ====== LOGIN & LOGOUT ======

def admin_login_view(request):
    if request.user.is_authenticated and is_manager(request.user):
        return redirect('custom_admin:dashboard')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        user = authenticate(request, username=email, password=password)
        if user is not None and (user.is_staff or user.is_manager or user.is_superuser):
            if user.is_suspended:
                messages.error(request, "This account is suspended.")
                return redirect('custom_admin:login')
            login(request, user)
            messages.success(request, f"Welcome to admin panel, {user.get_full_name() or user.username}.")
            return redirect('custom_admin:dashboard')
        messages.error(request, "Invalid credentials or you are not authorized to access the admin panel.")

    return render(request, 'custom_admin/login.html')


@login_required
def admin_logout_view(request):
    logout(request)
    messages.success(request, "Logged out from admin panel.")
    return redirect('custom_admin:login')


# ====== DASHBOARD ======

@user_passes_test(is_manager, login_url='custom_admin:login')
def dashboard_view(request):
    total_users = User.objects.count()
    total_clients = User.objects.filter(role=User.Role.CLIENT).count()
    total_specialists = User.objects.filter(role=User.Role.SPECIALIST).count()
    total_orders = Order.objects.count()
    
    # Platform revenue sum
    platform_revenue = Order.objects.filter(is_paid=True).aggregate(Sum('platform_fee'))['platform_fee__sum'] or Decimal('0.00')

    # Pending moderation / approvals counts
    pending_specialists = SpecialistProfile.objects.filter(is_approved=False).count()
    pending_messages = Message.objects.filter(message_type='TEXT', is_approved=False, is_rejected=False).count()

    # Recent list widgets
    recent_specialists = SpecialistProfile.objects.filter(is_approved=False).select_related('user').order_by('-created_at')[:5]
    recent_messages = Message.objects.filter(message_type='TEXT', is_approved=False, is_rejected=False).select_related('sender', 'conversation').order_by('-created_at')[:5]
    recent_orders = Order.objects.select_related('client', 'specialist', 'service').order_by('-created_at')[:5]
    recent_users = User.objects.order_by('-date_created')[:5]

    context = {
        'total_users': total_users,
        'total_clients': total_clients,
        'total_specialists': total_specialists,
        'total_orders': total_orders,
        'platform_revenue': platform_revenue,
        'pending_specialists': pending_specialists,
        'pending_messages': pending_messages,
        'recent_specialists': recent_specialists,
        'recent_messages': recent_messages,
        'recent_orders': recent_orders,
        'recent_users': recent_users,
    }
    return render(request, 'custom_admin/dashboard.html', context)


# ====== USER MANAGEMENT ======

@user_passes_test(is_manager, login_url='custom_admin:login')
def user_list_view(request):
    q = request.GET.get('q', '').strip()
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')

    users_qs = User.objects.exclude(id=request.user.id).order_by('-date_created')

    if q:
        users_qs = users_qs.filter(
            Q(username__icontains=q) |
            Q(email__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q)
        )

    if role_filter:
        users_qs = users_qs.filter(role=role_filter)

    if status_filter == 'suspended':
        users_qs = users_qs.filter(is_suspended=True)
    elif status_filter == 'active':
        users_qs = users_qs.filter(is_suspended=False)

    paginator = Paginator(users_qs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'users': page_obj,
        'page_obj': page_obj,
        'q': q,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'roles': User.Role.choices,
    }
    return render(request, 'custom_admin/users/list.html', context)


@user_passes_test(is_manager, login_url='custom_admin:login')
def user_detail_view(request, pk):
    target_user = get_object_or_404(User, pk=pk)
    
    # Get or create profiles depending on roles
    client_profile = None
    specialist_profile = None
    if target_user.is_client:
        client_profile, _ = ClientProfile.objects.get_or_create(user=target_user)
    elif target_user.is_specialist:
        specialist_profile, _ = SpecialistProfile.objects.get_or_create(user=target_user)

    user_form = UserForm(request.POST or None, instance=target_user)
    balance_form = BalanceForm(request.POST or None)

    # Process forms
    if request.method == 'POST':
        action_type = request.POST.get('form_action')
        
        if action_type == 'update_user':
            if user_form.is_valid():
                user_form.save()
                messages.success(request, f"User details for {target_user.username} updated.")
                return redirect('custom_admin:user_detail', pk=pk)
                
        elif action_type == 'update_balance':
            if balance_form.is_valid():
                action = balance_form.cleaned_data['action']
                amount = balance_form.cleaned_data['amount']
                
                profile = None
                if target_user.is_client:
                    profile = client_profile
                elif target_user.is_specialist:
                    profile = specialist_profile
                
                if profile is not None:
                    if action == 'credit':
                        profile.balance = (profile.balance or Decimal('0.00')) + amount
                        messages.success(request, f"Credited ${amount} to {target_user.username}'s balance.")
                    elif action == 'debit':
                        profile.balance = (profile.balance or Decimal('0.00')) - amount
                        messages.success(request, f"Debited ${amount} from {target_user.username}'s balance.")
                    elif action == 'set':
                        profile.balance = amount
                        messages.success(request, f"Set {target_user.username}'s balance to ${amount}.")
                    
                    profile.save(update_fields=['balance'])
                else:
                    messages.error(request, "This user does not have a specialist or client profile to manage balance.")
                
                return redirect('custom_admin:user_detail', pk=pk)

    context = {
        'target_user': target_user,
        'client_profile': client_profile,
        'specialist_profile': specialist_profile,
        'user_form': user_form,
        'balance_form': balance_form,
    }
    return render(request, 'custom_admin/users/detail.html', context)


@user_passes_test(is_manager, login_url='custom_admin:login')
def user_toggle_suspend(request, pk):
    target = get_object_or_404(User, pk=pk)
    if target.is_manager and not request.user.is_superuser:
        messages.error(request, "Only a superuser can suspend another manager.")
        return redirect('custom_admin:user_list')
    target.is_suspended = not target.is_suspended
    target.save(update_fields=['is_suspended'])
    messages.success(request, f"{target.username} has been {'suspended' if target.is_suspended else 'activated'}.")
    return redirect(request.META.get('HTTP_REFERER') or 'custom_admin:user_list')


@user_passes_test(is_manager, login_url='custom_admin:login')
def user_toggle_verify(request, pk):
    profile = get_object_or_404(SpecialistProfile, user_id=pk)
    profile.is_verified = not profile.is_verified
    profile.save(update_fields=['is_verified'])
    status = "verified" if profile.is_verified else "unverified"
    messages.success(request, f"Specialist {profile.user.username} is now {status}.")
    return redirect(request.META.get('HTTP_REFERER') or 'custom_admin:user_list')


@user_passes_test(is_manager, login_url='custom_admin:login')
def user_promote(request, pk):
    target = get_object_or_404(User, pk=pk)
    if not request.user.is_superuser:
        messages.error(request, "Only a superuser can promote/demote managers.")
        return redirect('custom_admin:user_list')
    
    if target.role == User.Role.MANAGER:
        target.role = User.Role.CLIENT
        ClientProfile.objects.get_or_create(user=target)
    else:
        target.role = User.Role.MANAGER
    target.save(update_fields=['role'])
    messages.success(request, f"{target.username}'s role changed to {target.get_role_display()}.")
    return redirect(request.META.get('HTTP_REFERER') or 'custom_admin:user_list')


# ====== SPECIALIST APPROVALS ======

@user_passes_test(is_manager, login_url='custom_admin:login')
def specialist_approval_list(request):
    pending = SpecialistProfile.objects.filter(is_approved=False).select_related('user').order_by('-created_at')
    paginator = Paginator(pending, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'custom_admin/approvals/list.html', {'pending': page_obj, 'page_obj': page_obj})


@user_passes_test(is_manager, login_url='custom_admin:login')
def specialist_approve(request, pk):
    profile = get_object_or_404(SpecialistProfile, pk=pk)
    profile.is_approved = True
    profile.save(update_fields=['is_approved'])
    messages.success(request, f"Specialist {profile.user.get_full_name() or profile.user.username} approved successfully.")
    return redirect(request.META.get('HTTP_REFERER') or 'custom_admin:specialist_approval_list')


@user_passes_test(is_manager, login_url='custom_admin:login')
def specialist_reject(request, pk):
    profile = get_object_or_404(SpecialistProfile, pk=pk)
    profile.is_approved = False
    profile.save(update_fields=['is_approved'])
    messages.warning(request, f"Specialist {profile.user.get_full_name() or profile.user.username} approval revoked.")
    return redirect(request.META.get('HTTP_REFERER') or 'custom_admin:specialist_approval_list')


# ====== CHAT MODERATION ======

@user_passes_test(is_manager, login_url='custom_admin:login')
def chat_moderation_list(request):
    pending = Message.objects.filter(message_type='TEXT', is_approved=False, is_rejected=False).select_related('sender', 'conversation').order_by('-created_at')
    paginator = Paginator(pending, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'custom_admin/moderation/list.html', {'pending': page_obj, 'page_obj': page_obj})


@user_passes_test(is_manager, login_url='custom_admin:login')
def chat_message_approve(request, pk):
    msg = get_object_or_404(Message, pk=pk)
    msg.is_approved = True
    msg.is_rejected = False
    msg.save(update_fields=['is_approved', 'is_rejected'])
    messages.success(request, f"Message #{msg.pk} from {msg.sender.username} approved.")
    return redirect(request.META.get('HTTP_REFERER') or 'custom_admin:chat_moderation_list')


@user_passes_test(is_manager, login_url='custom_admin:login')
def chat_message_reject(request, pk):
    msg = get_object_or_404(Message, pk=pk)
    msg.is_approved = False
    msg.is_rejected = True
    msg.save(update_fields=['is_approved', 'is_rejected'])
    messages.warning(request, f"Message #{msg.pk} from {msg.sender.username} rejected.")
    return redirect(request.META.get('HTTP_REFERER') or 'custom_admin:chat_moderation_list')


@user_passes_test(is_manager, login_url='custom_admin:login')
def chat_message_reply(request, pk):
    msg = get_object_or_404(Message.objects.select_related('conversation'), pk=pk)
    if request.method == 'POST':
        body = request.POST.get('body', '').strip()
        if body:
            Message.objects.create(conversation=msg.conversation, sender=request.user, body=body, is_approved=True)
            messages.success(request, 'Reply sent to the conversation.')
        else:
            messages.error(request, 'Write a reply before sending.')
    return redirect(request.META.get('HTTP_REFERER') or 'custom_admin:chat_moderation_list')


# ====== SERVICES ======

@user_passes_test(is_manager, login_url='custom_admin:login')
def service_list_view(request):
    q = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '')
    
    services_qs = Service.objects.select_related('specialist', 'category').order_by('-created_at')
    
    if q:
        services_qs = services_qs.filter(
            Q(title__icontains=q) |
            Q(description__icontains=q) |
            Q(specialist__username__icontains=q)
        )
    if category_id:
        services_qs = services_qs.filter(category_id=category_id)
        
    paginator = Paginator(services_qs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    categories = Category.objects.all()
    context = {
        'services': page_obj,
        'page_obj': page_obj,
        'categories': categories,
        'q': q,
        'category_id': category_id,
    }
    return render(request, 'custom_admin/services/list.html', context)


@user_passes_test(is_manager, login_url='custom_admin:login')
def service_detail_view(request, pk):
    service = get_object_or_404(
        Service.objects.select_related('specialist', 'category'),
        pk=pk,
    )
    reviews = service.reviews.select_related('reviewer').order_by('-created_at')
    return render(request, 'custom_admin/services/detail.html', {
        'service': service,
        'reviews': reviews,
    })


@user_passes_test(is_manager, login_url='custom_admin:login')
def service_toggle_active(request, pk):
    service = get_object_or_404(Service, pk=pk)
    service.is_active = not service.is_active
    service.save(update_fields=['is_active'])
    status = "activated" if service.is_active else "deactivated"
    messages.success(request, f"Service '{service.title}' is now {status}.")
    return redirect(request.META.get('HTTP_REFERER') or 'custom_admin:service_list')


@user_passes_test(is_manager, login_url='custom_admin:login')
def service_edit_view(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if request.method == 'POST':
        form = AdminServiceForm(request.POST, request.FILES, instance=service)
        if form.is_valid():
            form.save()
            messages.success(request, f"Service '{service.title}' updated successfully.")
            return redirect('custom_admin:service_detail', pk=service.pk)
    else:
        form = AdminServiceForm(instance=service)
    return render(request, 'custom_admin/services/form.html', {
        'form': form,
        'service': service,
        'title': f'Edit Service: {service.title}',
    })


@user_passes_test(is_manager, login_url='custom_admin:login')
def service_delete_view(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if request.method == 'POST':
        title = service.title
        service.delete()
        messages.success(request, f"Service '{title}' has been deleted.")
        return redirect('custom_admin:service_list')
    return render(request, 'custom_admin/services/confirm_delete.html', {'service': service})


# ====== CATEGORIES ======

@user_passes_test(is_manager, login_url='custom_admin:login')
def category_list_view(request):
    categories = Category.objects.all().order_by('name')
    return render(request, 'custom_admin/categories/list.html', {'categories': categories})


@user_passes_test(is_manager, login_url='custom_admin:login')
def category_create_view(request):
    form = CategoryForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        category = form.save(commit=False)
        if not category.slug:
            category.slug = slugify(category.name)
        category.save()
        messages.success(request, f"Category '{category.name}' created.")
        return redirect('custom_admin:category_list')
    
    return render(request, 'custom_admin/categories/form.html', {'form': form, 'title': 'Create Category'})


@user_passes_test(is_manager, login_url='custom_admin:login')
def category_edit_view(request, pk):
    category = get_object_or_404(Category, pk=pk)
    form = CategoryForm(request.POST or None, instance=category)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"Category '{category.name}' updated.")
        return redirect('custom_admin:category_list')
    
    return render(request, 'custom_admin/categories/form.html', {'form': form, 'title': 'Edit Category', 'category': category})


@user_passes_test(is_manager, login_url='custom_admin:login')
def category_delete_view(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        name = category.name
        category.delete()
        messages.success(request, f"Category '{name}' deleted.")
        return redirect('custom_admin:category_list')
    return render(request, 'custom_admin/categories/confirm_delete.html', {'category': category})


# ====== BLOG ======

@user_passes_test(is_manager, login_url='custom_admin:login')
def blog_list_view(request):
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    category_id = request.GET.get('category', '')
    posts = BlogPost.objects.select_related('author', 'category').order_by('-updated_at')
    if q:
        posts = posts.filter(Q(title__icontains=q) | Q(excerpt__icontains=q) | Q(content__icontains=q))
    if status:
        posts = posts.filter(status=status)
    if category_id:
        posts = posts.filter(category_id=category_id)
    page_obj = Paginator(posts, 10).get_page(request.GET.get('page'))
    return render(request, 'custom_admin/blog/list.html', {
        'posts': page_obj,
        'page_obj': page_obj,
        'categories': BlogCategory.objects.all(),
        'statuses': BlogPost.Status.choices,
        'q': q,
        'status_filter': status,
        'category_id': category_id,
    })


@user_passes_test(is_manager, login_url='custom_admin:login')
def blog_create_view(request):
    form = BlogPostForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        if post.status == BlogPost.Status.PUBLISHED and not post.published_at:
            post.published_at = timezone.now()
        post.save()
        messages.success(request, f"Blog post '{post.title}' created.")
        return redirect('custom_admin:blog_list')
    return render(request, 'custom_admin/blog/form.html', {'form': form, 'title': 'Create Blog Post'})


@user_passes_test(is_manager, login_url='custom_admin:login')
def blog_edit_view(request, pk):
    post = get_object_or_404(BlogPost, pk=pk)
    form = BlogPostForm(request.POST or None, request.FILES or None, instance=post)
    if request.method == 'POST' and form.is_valid():
        post = form.save(commit=False)
        if post.status == BlogPost.Status.PUBLISHED and not post.published_at:
            post.published_at = timezone.now()
        post.save()
        messages.success(request, f"Blog post '{post.title}' updated.")
        return redirect('custom_admin:blog_list')
    return render(request, 'custom_admin/blog/form.html', {'form': form, 'title': f'Edit: {post.title}', 'post': post})


@user_passes_test(is_manager, login_url='custom_admin:login')
def blog_delete_view(request, pk):
    post = get_object_or_404(BlogPost, pk=pk)
    if request.method == 'POST':
        title = post.title
        post.delete()
        messages.success(request, f"Blog post '{title}' deleted.")
        return redirect('custom_admin:blog_list')
    return render(request, 'custom_admin/blog/confirm_delete.html', {'post': post})


# ====== ORDERS ======

@user_passes_test(is_manager, login_url='custom_admin:login')
def order_list_view(request):
    q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')
    
    orders_qs = Order.objects.select_related('client', 'specialist', 'service').order_by('-created_at')
    
    if q:
        orders_qs = orders_qs.filter(
            Q(pk__icontains=q) |
            Q(requirements__icontains=q) |
            Q(client__username__icontains=q) |
            Q(specialist__username__icontains=q)
        )
    if status_filter:
        orders_qs = orders_qs.filter(status=status_filter)
        
    paginator = Paginator(orders_qs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    context = {
        'orders': page_obj,
        'page_obj': page_obj,
        'q': q,
        'status_filter': status_filter,
        'statuses': Order.Status.choices,
    }
    return render(request, 'custom_admin/orders/list.html', context)


@user_passes_test(is_manager, login_url='custom_admin:login')
def order_detail_view(request, pk):
    order = get_object_or_404(Order.objects.select_related('client', 'specialist', 'service'), pk=pk)
    documents = order.documents.select_related('uploaded_by')
    
    if request.method == 'POST':
        if request.POST.get('form_action') == 'deliver_order':
            document_form = OrderDocumentForm(request.POST, request.FILES)
            if document_form.is_valid():
                document = document_form.save(commit=False)
                document.order = order
                document.uploaded_by = request.user
                document.save()
                order.status = Order.Status.DELIVERED
                order.save(update_fields=['status', 'updated_at'])
                messages.success(request, f'Order #{order.pk} delivered with the uploaded file.')
                return redirect('custom_admin:order_detail', pk=pk)
        else:
            document_form = OrderDocumentForm()
            new_status = request.POST.get('status')
        if request.POST.get('form_action') != 'deliver_order' and new_status in dict(Order.Status.choices):
            order.status = new_status
            order.save(update_fields=['status', 'updated_at'])
            
            # If manager marks completed, credit specialist earnings
            if new_status == Order.Status.COMPLETED:
                sp, _ = SpecialistProfile.objects.get_or_create(user=order.specialist)
                sp.balance = (sp.balance or Decimal('0.00')) + order.specialist_earnings
                sp.save(update_fields=['balance'])
                
            messages.success(request, f"Order #{order.pk} status updated to {order.get_status_display()}.")
            return redirect('custom_admin:order_detail', pk=pk)
            
    context = {
        'order': order,
        'documents': documents,
        'document_form': locals().get('document_form', OrderDocumentForm()),
        'statuses': Order.Status.choices,
    }
    return render(request, 'custom_admin/orders/detail.html', context)


# ====== REVIEWS ======

@user_passes_test(is_manager, login_url='custom_admin:login')
def review_list_view(request):
    reviews_qs = Review.objects.select_related('service', 'reviewer', 'reviewee').order_by('-created_at')
    paginator = Paginator(reviews_qs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'custom_admin/reviews/list.html', {'reviews': page_obj, 'page_obj': page_obj})


@user_passes_test(is_manager, login_url='custom_admin:login')
def review_delete_view(request, pk):
    review = get_object_or_404(Review, pk=pk)
    if request.method == 'POST':
        review.delete()
        messages.success(request, "Review deleted.")
        return redirect('custom_admin:review_list')
    return render(request, 'custom_admin/reviews/confirm_delete.html', {'review': review})


# ====== INQUIRIES / CONTACT MESSAGES ======

@user_passes_test(is_manager, login_url='custom_admin:login')
def contact_list_view(request):
    q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    category_filter = request.GET.get('category', '').strip()

    messages_qs = ContactMessage.objects.select_related('user').order_by('-created_at')

    if q:
        messages_qs = messages_qs.filter(
            Q(name__icontains=q)
            | Q(email__icontains=q)
            | Q(subject__icontains=q)
            | Q(message__icontains=q)
            | Q(admin_notes__icontains=q)
        )
    if status_filter:
        messages_qs = messages_qs.filter(status=status_filter)
    if category_filter:
        messages_qs = messages_qs.filter(category=category_filter)

    paginator = Paginator(messages_qs, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    pending_count = ContactMessage.objects.filter(status=ContactMessage.Status.PENDING).count()

    context = {
        'inquiries': page_obj,
        'page_obj': page_obj,
        'q': q,
        'status_filter': status_filter,
        'category_filter': category_filter,
        'statuses': ContactMessage.Status.choices,
        'categories': ContactMessage.Category.choices,
        'pending_count': pending_count,
    }
    return render(request, 'custom_admin/inquiries/list.html', context)


@user_passes_test(is_manager, login_url='custom_admin:login')
def contact_detail_view(request, pk):
    from notifications.models import Notification
    from django.urls import reverse

    inquiry = get_object_or_404(ContactMessage.objects.select_related('user'), pk=pk)
    if request.method == 'POST':
        new_status = request.POST.get('status', '').strip()
        admin_notes = request.POST.get('admin_notes', '').strip()
        admin_reply = request.POST.get('admin_reply', '').strip()

        old_reply = inquiry.admin_reply
        old_status = inquiry.status

        if new_status in dict(ContactMessage.Status.choices):
            inquiry.status = new_status
        inquiry.admin_notes = admin_notes
        
        reply_changed = False
        if admin_reply:
            inquiry.admin_reply = admin_reply
            if admin_reply != old_reply:
                inquiry.replied_at = timezone.now()
                inquiry.is_read_by_user = False
                reply_changed = True

        inquiry.save(update_fields=['status', 'admin_notes', 'admin_reply', 'replied_at', 'is_read_by_user', 'updated_at'])
        
        # If user is registered, send them an in-app notification about response/status
        if inquiry.user and (reply_changed or (new_status and new_status != old_status)):
            notif_msg = f"Your inquiry '{inquiry.subject}' status is now '{inquiry.get_status_display()}'."
            if admin_reply and reply_changed:
                notif_msg += f"\nResponse: {admin_reply[:140]}"
            Notification.notify(
                recipient=inquiry.user,
                notif_type="ORDER_STATUS",
                title=f"Support Response: {inquiry.subject}",
                message=notif_msg,
                url=reverse("core:inquiry_detail", kwargs={"pk": inquiry.pk}),
            )

        messages.success(request, f"Inquiry #{inquiry.pk} updated successfully.")
        return redirect('custom_admin:contact_detail', pk=inquiry.pk)

    context = {
        'inquiry': inquiry,
        'statuses': ContactMessage.Status.choices,
    }
    return render(request, 'custom_admin/inquiries/detail.html', context)


@user_passes_test(is_manager, login_url='custom_admin:login')
def contact_delete_view(request, pk):
    inquiry = get_object_or_404(ContactMessage, pk=pk)
    if request.method == 'POST':
        subject = inquiry.subject
        inquiry.delete()
        messages.success(request, f"Inquiry '{subject}' has been deleted.")
        return redirect('custom_admin:contact_list')
    return render(request, 'custom_admin/inquiries/confirm_delete.html', {'inquiry': inquiry})

