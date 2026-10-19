from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0005_proposalchoice'),
    ]

    operations = [
        migrations.DeleteModel(name='BranchPrice'),
        migrations.DeleteModel(name='BasketBranch'),
        migrations.DeleteModel(name='ProposalChoice'),
        migrations.RemoveField(model_name='checkout', name='landed'),
        migrations.RemoveField(model_name='checkout', name='main_before'),
        migrations.RemoveField(model_name='checkout', name='main_after'),
        migrations.AlterField(model_name='checkout', name='state',
                              field=models.CharField(default='launching', max_length=20)),
        migrations.CreateModel(
            name='BasketChoice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item', models.CharField(max_length=100, unique=True)),
                ('version', models.CharField(max_length=64)),
                ('choice', models.CharField(max_length=10)),
                ('by', models.CharField(max_length=150)),
                ('at', models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ['item']},
        ),
        migrations.CreateModel(
            name='BasketAnswer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item', models.CharField(max_length=100)),
                ('number', models.PositiveIntegerField()),
                ('question', models.TextField()),
                ('answer', models.TextField()),
                ('by', models.CharField(max_length=150)),
                ('at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['item', 'number'],
                'constraints': [models.UniqueConstraint(fields=('item', 'number'), name='one_answer_a_question')],
            },
        ),
    ]
