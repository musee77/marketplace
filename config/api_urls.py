from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token

from django.urls import path, include

from accounts.api_views import UserViewSet, SpecialistProfileViewSet, ClientProfileViewSet
from services.api_views import ServiceViewSet, CategoryViewSet
from orders.api_views import OrderViewSet
from reviews.api_views import ReviewViewSet

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("specialists", SpecialistProfileViewSet, basename="specialistprofile")
router.register("clients", ClientProfileViewSet, basename="clientprofile")
router.register("categories", CategoryViewSet, basename="category")
router.register("services", ServiceViewSet, basename="service")
router.register("orders", OrderViewSet, basename="order")
router.register("reviews", ReviewViewSet, basename="review")

urlpatterns = [
    path("token/", obtain_auth_token, name="api_token_auth"),
    path("", include(router.urls)),
]
