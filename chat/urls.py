from django.urls import path
from . import views

app_name = "chat"

urlpatterns = [
    path("", views.inbox, name="inbox"),
    path("<int:pk>/", views.conversation_detail, name="conversation"),
    path("start/<int:user_id>/", views.start_conversation, name="start"),
    path("moderate/", views.moderate_messages, name="moderate"),
    path("moderate/<int:pk>/approve/", views.approve_message, name="approve"),
    path("moderate/<int:pk>/reject/", views.reject_message, name="reject"),
    path("system/", views.system_chat, name="system_chat"),
    path("attachment/<int:pk>/download/", views.chat_attachment_download, name="attachment_download"),
]
