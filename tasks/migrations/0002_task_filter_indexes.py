from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tasks", "0001_initial"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="task",
            index=models.Index(fields=["priority", "status"], name="tasks_task_priorit_6c5a5e_idx"),
        ),
        migrations.AddIndex(
            model_name="task",
            index=models.Index(fields=["due_date"], name="tasks_task_due_date_3cf8f4_idx"),
        ),
    ]
