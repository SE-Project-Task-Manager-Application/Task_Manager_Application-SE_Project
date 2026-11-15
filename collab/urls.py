from django.urls import path

from . import views

app_name = "collab"

urlpatterns = [
    path("<int:pk>/comments/", views.TaskCommentsView.as_view(), name="task_comments"),
    path("<int:pk>/activity/", views.TaskActivityView.as_view(), name="task_activity"),
]
