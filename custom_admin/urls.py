from django.urls import path
from . import views

app_name = 'custom_admin'

urlpatterns = [
    path('login/', views.admin_login_view, name='login'),
    path('logout/', views.admin_logout_view, name='logout'),
    path('', views.dashboard_view, name='dashboard'),
    
    # Users
    path('users/', views.user_list_view, name='user_list'),
    path('users/<int:pk>/', views.user_detail_view, name='user_detail'),
    path('users/<int:pk>/toggle-suspend/', views.user_toggle_suspend, name='user_toggle_suspend'),
    path('users/<int:pk>/toggle-verify/', views.user_toggle_verify, name='user_toggle_verify'),
    path('users/<int:pk>/promote/', views.user_promote, name='user_promote'),
    
    # Approvals
    path('approvals/', views.specialist_approval_list, name='specialist_approval_list'),
    path('approvals/<int:pk>/approve/', views.specialist_approve, name='specialist_approve'),
    path('approvals/<int:pk>/reject/', views.specialist_reject, name='specialist_reject'),
    
    # Chat Moderation
    path('moderation/', views.chat_moderation_list, name='chat_moderation_list'),
    path('moderation/<int:pk>/approve/', views.chat_message_approve, name='chat_message_approve'),
    path('moderation/<int:pk>/reject/', views.chat_message_reject, name='chat_message_reject'),
    path('moderation/<int:pk>/reply/', views.chat_message_reply, name='chat_message_reply'),
    
    # Services
    path('services/', views.service_list_view, name='service_list'),
    path('services/<int:pk>/', views.service_detail_view, name='service_detail'),
    path('services/<int:pk>/toggle-active/', views.service_toggle_active, name='service_toggle_active'),
    
    # Categories
    path('categories/', views.category_list_view, name='category_list'),
    path('categories/create/', views.category_create_view, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_edit_view, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete_view, name='category_delete'),

    # Blog
    path('blog/', views.blog_list_view, name='blog_list'),
    path('blog/create/', views.blog_create_view, name='blog_create'),
    path('blog/<int:pk>/edit/', views.blog_edit_view, name='blog_edit'),
    path('blog/<int:pk>/delete/', views.blog_delete_view, name='blog_delete'),
    
    # Orders
    path('orders/', views.order_list_view, name='order_list'),
    path('orders/<int:pk>/', views.order_detail_view, name='order_detail'),
    
    # Reviews
    path('reviews/', views.review_list_view, name='review_list'),
    path('reviews/<int:pk>/delete/', views.review_delete_view, name='review_delete'),
]
