from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path("inquiries/", views.my_inquiries, name="my_inquiries"),
    path("inquiries/<int:pk>/", views.inquiry_detail, name="inquiry_detail"),
    path("my-inquiries/", views.my_inquiries, name="my_inquiries_alias"),
    path("dashboard/", views.dashboard, name="dashboard"),
]
