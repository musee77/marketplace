from django.urls import path
from . import views

app_name = "services"

urlpatterns = [
    path("", views.service_list, name="list"),
    path("mine/", views.my_services, name="mine"),
    path("new/", views.service_create, name="create"),
    path("<slug:slug>/", views.service_detail, name="detail"),
    path("<slug:slug>/edit/", views.service_edit, name="edit"),
    path("<slug:slug>/delete/", views.service_delete, name="delete"),
]
