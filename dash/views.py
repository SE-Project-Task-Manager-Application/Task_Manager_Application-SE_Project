"""Dashboard (TM-F-040) and CSV export (TM-F-041) views."""

import datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.views.generic import ListView, View

from . import services


def _parse_date(value):
    """Parse a YYYY-MM-DD form value; return None for empty or invalid input."""
    if not value:
        return None
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        return None


class RangeParamsMixin:
    """Read the optional start/end range from GET parameters."""

    def range_params(self):
        start = _parse_date(self.request.GET.get("start"))
        end = _parse_date(self.request.GET.get("end"))
        if start and end and end < start:
            start, end = end, start
        return start, end


class DashboardView(LoginRequiredMixin, RangeParamsMixin, ListView):
    """Open/overdue/completed summary for the user's tasks over a chosen range."""

    template_name = "dash/dashboard.html"
    context_object_name = "tasks"
    paginate_by = 50

    def get_queryset(self):
        start, end = self.range_params()
        tasks, self.counts = services.summary_for(self.request.user, start, end)
        return tasks

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        start, end = self.range_params()
        context["counts"] = self.counts
        context["start"] = start
        context["end"] = end
        return context


class DashboardCSVExportView(LoginRequiredMixin, RangeParamsMixin, View):
    """Download the same rows and totals as the dashboard, as CSV (TM-F-041)."""

    def get(self, request, *args, **kwargs):
        start, end = self.range_params()
        tasks, counts = services.summary_for(request.user, start, end)
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="dashboard.csv"'
        services.export_csv(response, tasks, counts)
        return response
