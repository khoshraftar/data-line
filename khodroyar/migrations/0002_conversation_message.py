# Generated by Django 5.2.3 on 2025-07-15 16:28

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('khodroyar', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Conversation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('conversation_id', models.CharField(db_index=True, max_length=255, unique=True, verbose_name='شناسه مکالمه')),
                ('title', models.CharField(blank=True, max_length=500, null=True, verbose_name='عنوان مکالمه')),
                ('is_active', models.BooleanField(default=True, verbose_name='فعال')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='تاریخ ایجاد')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')),
                ('user_auth', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='khodroyar.userauth', verbose_name='کاربر')),
            ],
            options={
                'verbose_name': 'مکالمه',
                'verbose_name_plural': 'مکالمات',
            },
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message_type', models.CharField(choices=[('user', 'کاربر'), ('bot', 'ربات')], max_length=10, verbose_name='نوع پیام')),
                ('content', models.TextField(verbose_name='محتوای پیام')),
                ('metadata', models.JSONField(blank=True, default=dict, verbose_name='متادیتا')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='تاریخ ایجاد')),
                ('conversation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='khodroyar.conversation', verbose_name='مکالمه')),
            ],
            options={
                'verbose_name': 'پیام',
                'verbose_name_plural': 'پیام\u200cها',
                'ordering': ['created_at'],
            },
        ),
    ]
