from django.urls import path

from . import views

app_name = "collab"

urlpatterns = [
    path("<int:pk>/comments/", views.TaskCommentsView.as_view(), name="task_comments"),
]
