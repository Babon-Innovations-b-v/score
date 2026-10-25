from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0008_checkout_pid"),
    ]

    operations = [
        migrations.AddField(model_name="checkout", name="design_at",
                            field=models.CharField(blank=True, max_length=32)),
    ]
