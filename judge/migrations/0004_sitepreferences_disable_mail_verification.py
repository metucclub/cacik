# Generated by Django 2.2.6 on 2019-10-28 15:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0003_auto_20191028_1544'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitepreferences',
            name='disable_mail_verification',
            field=models.BooleanField(default=False),
        ),
    ]
