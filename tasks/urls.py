from django.urls import path

from . import views
from collab.views import TaskShareView

app_name = "tasks"

urlpatterns = [
    path("", views.TaskListView.as_view(), name="list"),
    path("new/", views.TaskCreateView.as_view(), name="create"),
    path("<int:task_id>/share/", TaskShareView.as_view(), name="share"),
    path("<int:pk>/edit/", views.TaskEditView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.delete_task, name="delete"),
    path("<int:pk>/restore/", views.restore_task, name="restore"),
    path("<int:pk>/complete/", views.complete_task, name="complete"),
    path("<int:pk>/reopen/", views.reopen_task, name="reopen"),
]
