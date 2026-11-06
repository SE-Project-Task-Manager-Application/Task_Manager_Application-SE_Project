from django.urls import path

from . import views

app_name = "adminpanel"

urlpatterns = [
    path("", views.user_list, name="index"),
    path("users/", views.user_list, name="user_list"),
    path("users/<int:user_id>/disable/", views.disable_user, name="disable_user"),
    path("users/<int:user_id>/enable/", views.enable_user, name="enable_user"),
    path("users/<int:user_id>/delete/", views.delete_user, name="delete_user"),
    path("categories/", views.category_list, name="category_list"),
    path("categories/<int:label_id>/rename/", views.category_rename, name="category_rename"),
    path("categories/<int:label_id>/archive/", views.category_archive, name="category_archive"),
    path("categories/<int:label_id>/restore/", views.category_restore, name="category_restore"),
]