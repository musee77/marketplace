from django.urls import path
from . import views

app_name = "reviews"

urlpatterns = [
    path("order/<int:order_pk>/new/", views.review_create, name="create"),
]
