from django.contrib.auth.views import LogoutView
from django.urls import reverse_lazy
from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("logged-out/", views.logged_out, name="logged_out"),
    path("profile/edit/", views.edit_profile, name="edit_profile"),
    path("referrals/", views.referrals_view, name="referrals"),
    path("funds/add/", views.add_funds, name="add_funds"),
    path("specialist/<int:pk>/reviews/", views.specialist_reviews, name="specialist_reviews"),
    path("specialist/<int:pk>/", views.SpecialistPublicProfileView.as_view(), name="specialist_public"),
    path("specialists/", views.specialist_list, name="specialist_list"),

    path("manage/users/", views.manager_user_list, name="manager_user_list"),
    path("manage/users/<int:pk>/toggle-suspend/", views.manager_toggle_suspend, name="manager_toggle_suspend"),
    path("manage/users/<int:pk>/toggle-verify/", views.manager_toggle_verify, name="manager_toggle_verify"),
    path("manage/users/<int:pk>/toggle-manager/", views.manager_promote, name="manager_promote"),
    path("manage/users/<int:pk>/balance/", views.manager_manage_balance, name="manager_manage_balance"),
    path("manage/pending-specialists/", views.manager_pending_specialists, name="pending_specialists"),
    path("manage/users/<int:pk>/toggle-approve/", views.manager_toggle_approve, name="manager_toggle_approve"),
    path("admin-login/", views.admin_login, name="admin_login"),
    path("settings/password/", views.password_change, name="password_change"),
]
