from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0009_checkout_design_at"),
    ]

    operations = [
        migrations.AddField(model_name="checkout", name="chat_yes", field=models.JSONField(blank=True, default=dict)),
    ]
