from django.db import models

# Create your models here.

class UserAuth(models.Model):
    user_id = models.CharField(max_length=255, unique=True, verbose_name='شناسه کاربر', db_index=True)
    access_token = models.TextField(verbose_name='توکن دسترسی')
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='شماره تلفن', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد', db_index=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')

    def __str__(self):
        return f"User {self.user_id}"

    class Meta:
        verbose_name = 'احراز هویت کاربر'
        verbose_name_plural = 'احراز هویت کاربران'
