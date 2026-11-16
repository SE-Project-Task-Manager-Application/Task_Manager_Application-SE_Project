from django.urls import path

from . import views

app_name = "dash"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="index"),
    path("export.csv", views.DashboardCSVExportView.as_view(), name="export_csv"),
]
