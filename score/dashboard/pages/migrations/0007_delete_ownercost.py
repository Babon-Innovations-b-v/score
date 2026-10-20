from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0006_basketchoice"),
    ]

    operations = [
        migrations.DeleteModel(name="OwnerCost"),
    ]
