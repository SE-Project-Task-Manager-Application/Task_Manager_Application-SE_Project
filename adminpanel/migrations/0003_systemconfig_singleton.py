from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("adminpanel", "0002_systemconfig")]

    operations = [
        migrations.AddConstraint(
            model_name="systemconfig",
            constraint=models.CheckConstraint(
                condition=models.Q(pk=1),
                name="system_config_singleton",
            ),
        ),
    ]
