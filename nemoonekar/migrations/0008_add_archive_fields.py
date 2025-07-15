# Generated manually for archive functionality

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nemoonekar', '0007_samplework_is_reviewed'),
    ]

    operations = [
        migrations.AddField(
            model_name='samplework',
            name='is_archived',
            field=models.BooleanField(default=False, verbose_name='آرشیو شده'),
        ),
        migrations.AddField(
            model_name='samplework',
            name='archived_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='تاریخ آرشیو'),
        ),
    ] 