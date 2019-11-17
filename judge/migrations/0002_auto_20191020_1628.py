# Generated by Django 2.1.13 on 2019-10-20 16:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='contest',
            name='hide_submission_feedback',
            field=models.BooleanField(default=True, help_text='Hide submission feedback on submssion page.', verbose_name='hide submission feedback'),
        ),
        migrations.AlterField(
            model_name='contest',
            name='hide_participation_tab',
            field=models.BooleanField(default=False, help_text='Hide participation tab on contest page.', verbose_name='hide participation tab'),
        ),
        migrations.AlterField(
            model_name='contest',
            name='hide_points',
            field=models.BooleanField(default=False, help_text='Hide problem points on all pages', verbose_name='hide points'),
        ),
        migrations.AlterField(
            model_name='contest',
            name='no_social_share',
            field=models.BooleanField(default=False, help_text='Disable social share buttons on contest page.', verbose_name='disable social share buttons'),
        ),
    ]