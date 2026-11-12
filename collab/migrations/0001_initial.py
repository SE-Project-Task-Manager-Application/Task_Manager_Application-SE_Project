# Generated for TM-F-030 task sharing.
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("tasks", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="TaskShare",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("permission", models.CharField(choices=[("viewer", "Viewer"), ("editor", "Editor")], max_length=10)),
                ("shared_at", models.DateTimeField(auto_now_add=True)),
                ("shared_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_task_shares", to=settings.AUTH_USER_MODEL)),
                ("task", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="shares", to="tasks.task")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="task_shares", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["shared_at", "id"]},
        ),
        migrations.AddConstraint(
            model_name="taskshare",
            constraint=models.UniqueConstraint(fields=("task", "user"), name="unique_task_share"),
        ),
    ]
