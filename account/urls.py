from django.urls import path
from django.contrib.auth import views as auth_views
from account import views

app_name = "account"
urlpatterns = [
        path("login", auth_views.LoginView.as_view(template_name="account/login.html"), name="login"),
        path("logout", auth_views.LogoutView.as_view(template_name="account/logout.html"), name="logout"),
        path("confirm-logout", views.confirm_logout, name="confirm-logout" ),
        path("password-reset", auth_views.PasswordResetView.as_view(template_name="account/password_reset.html"), name="password_reset"),
        
        ]
