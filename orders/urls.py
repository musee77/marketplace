from django.urls import path
from . import views

app_name = "orders"

urlpatterns = [
    path("", views.order_list, name="list"),
    path("place/", views.order_create_quick, name="create_quick"),
    path("place/<slug:slug>/", views.order_create, name="create"),
    path("<int:pk>/pay/", views.order_pay, name="pay"),
    path("<int:pk>/cancel/", views.order_cancel, name="cancel"),
    path("<int:pk>/decide/", views.order_decide, name="decide"),
    path("<int:pk>/revision/", views.order_request_revision, name="request_revision"),
    path("<int:pk>/documents/upload/", views.order_document_upload, name="document_upload"),
    path("<int:pk>/deliver/", views.order_deliver, name="deliver"),
    path("documents/<int:pk>/download/", views.order_document_download, name="document_download"),
    path("<int:pk>/", views.order_detail, name="detail"),
    path("<int:pk>/set/<str:new_status>/", views.order_transition, name="transition"),
    path("paystack/callback/", views.paystack_callback, name="paystack_callback"),
    
    # Offer endpoints
    path("offers/", views.offer_list_received, name="offer_list"),
    path("offers/sent/", views.offer_list_sent, name="offer_list_sent"),
    path("offers/<int:pk>/", views.offer_detail, name="offer_detail"),
    path("offers/<int:pk>/accept/", views.offer_accept, name="offer_accept"),
    path("offers/<int:pk>/decline/", views.offer_decline, name="offer_decline"),
    path("offers/messages/<int:pk>/edit/", views.offer_message_edit, name="offer_message_edit"),
    path("offers/messages/<int:pk>/delete/", views.offer_message_delete, name="offer_message_delete"),
    path("offers/to/<int:client_id>/", views.offer_create, name="offer_create"),
]
