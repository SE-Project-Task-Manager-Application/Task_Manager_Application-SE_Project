"""Dashboard summary (TM-F-040) and CSV export (TM-F-041), SAD 4.5.

Both the dashboard page and the CSV export read from the same queryset built
here, so the on-screen totals and the downloaded file always match (SAD 4.5).

Definitions:
- open: status "todo" or "in_progress" (not done, not soft-deleted);
- overdue: not done and due_date in the past;
- completed: status "done".

The chosen range filters on due_date: a task is in the range when its due
date falls between the start (inclusive) and the end (inclusive). Tasks
without a due date have no date to place in a range, so they appear only
when no range is chosen.
"""

import csv
import datetime

from django.db.models import Q
from django.utils import timezone

from tasks.models import Task

OPEN_STATUSES = (Task.Status.TODO, Task.Status.IN_PROGRESS)


def visible_tasks(user):
    """Active tasks the user owns or is assigned to (same scope as the task list)."""
    return (
        Task.objects.active()
        .filter(Q(owner=user) | Q(assignments__user=user))
        .select_related("owner")
        .prefetch_related("labels", "assignees")
        .distinct()
    )


def in_range(queryset, start=None, end=None):
    """Keep tasks whose due_date is inside [start, end] (dates, inclusive).

    With no range the queryset is returned unchanged.
    """
    if start is None and end is None:
        return queryset
    queryset = queryset.filter(due_date__isnull=False)
    if start is not None:
        queryset = queryset.filter(
            due_date__gte=timezone.make_aware(datetime.datetime.combine(start, datetime.time.min))
        )
    if end is not None:
        queryset = queryset.filter(
            due_date__lte=timezone.make_aware(datetime.datetime.combine(end, datetime.time.max))
        )
    return queryset


def summarize(queryset, now=None):
    """Counts for the queryset: open, overdue and completed."""
    now = now or timezone.now()
    open_count = queryset.filter(status__in=OPEN_STATUSES).count()
    overdue_count = (
        queryset.filter(status__in=OPEN_STATUSES, due_date__isnull=False, due_date__lt=now).count()
    )
    completed_count = queryset.filter(status=Task.Status.DONE).count()
    return {
        "open": open_count,
        "overdue": overdue_count,
        "completed": completed_count,
        "total": queryset.count(),
    }


def summary_for(user, start=None, end=None, now=None):
    """The dashboard's queryset plus its counts, from one shared query."""
    tasks = in_range(visible_tasks(user), start, end)
    return tasks, summarize(tasks, now=now)


CSV_COLUMNS = ("title", "status", "priority", "due_date", "owner", "assignees", "labels")


def task_row(task):
    """One CSV row for a task, using display values like the web UI."""
    return (
        task.title,
        task.get_status_display(),
        task.get_priority_display(),
        timezone.localtime(task.due_date).strftime("%Y-%m-%d %H:%M") if task.due_date else "",
        task.owner.email,
        ", ".join(person.email for person in task.assignees.all()),
        ", ".join(label.name for label in task.labels.all()),
    )


def export_csv(fileobj, tasks, counts):
    """Write the task rows and the summary counts to a CSV file object.

    The summary block repeats the on-screen totals so the exported file can be
    checked against the dashboard (TM-F-041 acceptance).
    """
    writer = csv.writer(fileobj)
    writer.writerow(CSV_COLUMNS)
    for task in tasks:
        writer.writerow(task_row(task))
    writer.writerow(())
    writer.writerow(("Summary", "Count"))
    writer.writerow(("Open", counts["open"]))
    writer.writerow(("Overdue", counts["overdue"]))
    writer.writerow(("Completed", counts["completed"]))
    writer.writerow(("Total", counts["total"]))
