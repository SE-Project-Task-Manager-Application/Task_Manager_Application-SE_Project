from django.urls import path

from . import views

app_name = "storage"

urlpatterns = [
    path("tasks/<int:task_id>/attachments/upload/", views.upload_attachment, name="upload"),
    path("attachments/<int:attachment_id>/download/", views.download_attachment, name="download"),
]
