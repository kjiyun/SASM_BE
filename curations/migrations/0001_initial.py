# Generated by Django 4.0 on 2023-04-06 23:20

import curations.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('stories', '0012_story_place'),
        ('users', '0008_rename_is_sdp_user_is_sdp_admin'),
    ]

    operations = [
        migrations.CreateModel(
            name='Curation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(max_length=100)),
                ('rep_pic', models.ImageField(default='curation_rep_pic.png', upload_to=curations.models.get_upload_path)),
                ('tags', models.CharField(max_length=200)),
                ('view_cnt', models.PositiveIntegerField(default=0, verbose_name='조회수')),
                ('supports_comments', models.BooleanField(default=False)),
                ('show_viewcount', models.BooleanField(default=False)),
                ('is_released', models.BooleanField(default=False)),
                ('is_selected', models.BooleanField(default=False)),
                ('is_rep', models.BooleanField(default=False)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='CurationPhoto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('image', models.ImageField(default='curation_image.png', upload_to=curations.models.get_upload_path)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Curation_Story',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('short_curation', models.CharField(max_length=200)),
                ('curation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='curations.curation')),
                ('story', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='stories.story')),
            ],
            options={
                'db_table': 'curation_story',
            },
        ),
        migrations.AddField(
            model_name='curation',
            name='story',
            field=models.ManyToManyField(related_name='curations', through='curations.Curation_Story', to='stories.Story'),
        ),
        migrations.AddField(
            model_name='curation',
            name='story_likeuser_set',
            field=models.ManyToManyField(blank=True, related_name='CurationLikeUser', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='curation',
            name='writer',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='curations', to='users.user'),
        ),
    ]