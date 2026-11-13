from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("adminpanel", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="SystemConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("password_min_length", models.PositiveSmallIntegerField(default=8)),
                ("session_timeout_seconds", models.PositiveIntegerField(default=86400)),
                ("notifications_enabled", models.BooleanField(default=True)),
                ("notification_sender", models.EmailField(default="no-reply@example.com", max_length=254)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "system configuration"},
        ),
    ]
