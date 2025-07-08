from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
import os

def sample_work_image_path(instance, filename):
    """Generate file path for sample work images"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return f'sample_works/{instance.sample_work.uuid}/{filename}'

# Create your models here.

class UserAuth(models.Model):
    user_id = models.CharField(max_length=255, unique=True, verbose_name='شناسه کاربر')
    access_token = models.TextField(verbose_name='توکن دسترسی')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')

    def __str__(self):
        return f"User {self.user_id}"

    class Meta:
        verbose_name = 'احراز هویت کاربر'
        verbose_name_plural = 'احراز هویت کاربران'


class SampleWork(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True, verbose_name='شناسه یکتا')
    title = models.CharField(max_length=200, verbose_name='عنوان')
    post_token = models.CharField(max_length=8, unique=True, verbose_name='توکن پست')
    user = models.ForeignKey(UserAuth, on_delete=models.CASCADE, verbose_name='کاربر')
    description = models.TextField(verbose_name='توضیحات')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['created_at']
        verbose_name = 'نمونه کار'
        verbose_name_plural = 'نمونه کارها'

class PostImage(models.Model):
    image = models.ImageField(upload_to=sample_work_image_path, verbose_name='تصویر')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    sample_work = models.ForeignKey(SampleWork, on_delete=models.CASCADE, verbose_name='نمونه کار')

    def __str__(self):
        return f"Image for {self.sample_work.title}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'تصویر پست'
        verbose_name_plural = 'تصاویر پست'
