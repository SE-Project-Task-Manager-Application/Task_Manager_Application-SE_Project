from django.urls import path

from . import views
from collab.views import TaskShareView

app_name = "tasks"

urlpatterns = [
    path("", views.TaskListView.as_view(), name="list"),
    path("new/", views.TaskCreateView.as_view(), name="create"),
    path("<int:task_id>/share/", TaskShareView.as_view(), name="share"),
]
