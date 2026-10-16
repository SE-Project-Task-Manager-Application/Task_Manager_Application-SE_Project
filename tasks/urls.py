from django.urls import path

from . import views

app_name = "tasks"

urlpatterns = [
    path("", views.TaskListView.as_view(), name="list"),
    path("new/", views.TaskCreateView.as_view(), name="create"),
]
