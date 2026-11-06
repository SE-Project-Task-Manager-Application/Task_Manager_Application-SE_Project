from django.urls import path

from . import views

app_name = "adminpanel"

urlpatterns = [
    path("", views.user_list, name="index"),
    path("users/", views.user_list, name="user_list"),
    path("audit/", views.audit_log, name="audit_log"),
    path("users/<int:user_id>/disable/", views.disable_user, name="disable_user"),
    path("users/<int:user_id>/enable/", views.enable_user, name="enable_user"),
    path("users/<int:user_id>/delete/", views.delete_user, name="delete_user"),
]