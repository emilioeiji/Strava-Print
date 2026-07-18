"""Root URL configuration."""

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from studio.views import SignUpView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("entrar/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("sair/", auth_views.LogoutView.as_view(), name="logout"),
    path("criar-conta/", SignUpView.as_view(), name="signup"),
    path("", include("studio.urls")),
]
