from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage
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
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='شماره تلفن')
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
    image = models.ImageField(
        upload_to=sample_work_image_path, 
        verbose_name='تصویر',
        storage=S3Boto3Storage()
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    sample_work = models.ForeignKey(SampleWork, on_delete=models.CASCADE, verbose_name='نمونه کار')

    def __str__(self):
        return f"Image for {self.sample_work.title}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'تصویر پست'
        verbose_name_plural = 'تصاویر پست'


class Payment(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'در انتظار پرداخت'),
        ('completed', 'پرداخت شده'),
        ('failed', 'ناموفق'),
        ('cancelled', 'لغو شده'),
    ]
    
    sample_work = models.ForeignKey(SampleWork, on_delete=models.CASCADE, verbose_name='نمونه کار')
    amount = models.IntegerField(verbose_name='مبلغ (ریال)')
    authority = models.CharField(max_length=255, blank=True, null=True, verbose_name='کد مرجع')
    ref_id = models.CharField(max_length=255, blank=True, null=True, verbose_name='شماره پیگیری')
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending', verbose_name='وضعیت')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')
    
    def __str__(self):
        return f"Payment for {self.sample_work.title} - {self.get_status_display()}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'پرداخت'
        verbose_name_plural = 'پرداخت‌ها'


class PostAddon(models.Model):
    ADDON_STATUS_CHOICES = [
        ('pending', 'در انتظار'),
        ('created', 'ایجاد شده'),
        ('failed', 'ناموفق'),
    ]
    
    ADDON_TYPE_CHOICES = [
        ('premium', 'پریمیوم'),
        ('urgent', 'فوری'),
        ('vip', 'ویژه'),
    ]
    
    sample_work = models.ForeignKey(SampleWork, on_delete=models.CASCADE, verbose_name='نمونه کار')
    duration = models.IntegerField(verbose_name='مدت زمان (روز)')
    status = models.CharField(max_length=20, choices=ADDON_STATUS_CHOICES, default='pending', verbose_name='وضعیت')
    addon_id = models.CharField(max_length=255, blank=True, null=True, verbose_name='شناسه افزونه')
    error_message = models.TextField(blank=True, null=True, verbose_name='پیام خطا')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')
    
    def __str__(self):
        return f"Addon for {self.sample_work.title} - {self.get_addon_type_display()}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'افزونه پست'
        verbose_name_plural = 'افزونه‌های پست'
