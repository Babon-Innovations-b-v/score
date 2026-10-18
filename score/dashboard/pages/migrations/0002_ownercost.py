from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="OwnerCost",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source", models.CharField(max_length=30)),
                ("month", models.CharField(max_length=7)),
                ("euros", models.FloatField()),
                ("words", models.CharField(blank=True, max_length=200)),
                ("by", models.CharField(max_length=150)),
                ("at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-at"]},
        ),
    ]
