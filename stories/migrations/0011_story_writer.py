# Generated by Django 4.0 on 2023-04-02 07:16

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_rename_is_sdp_user_is_sdp_admin'),
        ('stories', '0010_alter_storycomment_mention_alter_storycomment_parent_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='story',
            name='writer',
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='stories', to='users.user'),
        ),
    ]
