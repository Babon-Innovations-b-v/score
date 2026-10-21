from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0007_delete_ownercost"),
    ]

    operations = [
        migrations.AddField(model_name="checkout", name="pid", field=models.IntegerField(blank=True, null=True)),
    ]
