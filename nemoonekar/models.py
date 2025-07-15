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


class SampleWorkManager(models.Manager):
    """Custom manager to filter out archived sample works by default"""
    
    def get_queryset(self):
        return super().get_queryset().filter(is_archived=False)
    
    def all_including_archived(self):
        """Return all sample works including archived ones"""
        return super().get_queryset()
    
    def archived(self):
        """Return only archived sample works"""
        return super().get_queryset().filter(is_archived=True)


class SampleWork(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True, verbose_name='شناسه یکتا')
    title = models.CharField(max_length=200, verbose_name='عنوان')
    post_token = models.CharField(max_length=8, unique=True, verbose_name='توکن پست', db_index=True)
    user = models.ForeignKey(UserAuth, on_delete=models.CASCADE, verbose_name='کاربر', db_index=True)
    description = models.TextField(verbose_name='توضیحات')
    is_reviewed = models.BooleanField(default=False, verbose_name='بررسی شده', db_index=True)
    is_archived = models.BooleanField(default=False, verbose_name='آرشیو شده', db_index=True)
    archived_at = models.DateTimeField(blank=True, null=True, verbose_name='تاریخ آرشیو', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد', db_index=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی', db_index=True)

    # Use custom manager
    objects = SampleWorkManager()

    def __str__(self):
        return self.title

    @classmethod
    def all_including_archived(cls):
        """Return all sample works including archived ones"""
        return cls.objects.all_including_archived()
    
    @classmethod
    def archived(cls):
        """Return only archived sample works"""
        return cls.objects.archived()

    def archive(self):
        """Archive the sample work instead of deleting it"""
        self.is_archived = True
        self.archived_at = timezone.now()
        self.save()

    def unarchive(self):
        """Unarchive the sample work"""
        self.is_archived = False
        self.archived_at = None
        self.save()

    class Meta:
        ordering = ['created_at']
        verbose_name = 'نمونه کار'
        verbose_name_plural = 'نمونه کارها'
        indexes = [
            models.Index(fields=['user', 'is_archived']),
            models.Index(fields=['is_reviewed', 'is_archived']),
            models.Index(fields=['created_at', 'is_archived']),
        ]

class PostImage(models.Model):
    image = models.ImageField(
        upload_to=sample_work_image_path, 
        verbose_name='تصویر',
        storage=S3Boto3Storage()
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد', db_index=True)
    sample_work = models.ForeignKey(SampleWork, on_delete=models.CASCADE, verbose_name='نمونه کار', db_index=True)

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
    
    sample_work = models.ForeignKey(SampleWork, on_delete=models.CASCADE, verbose_name='نمونه کار', db_index=True)
    amount = models.IntegerField(verbose_name='مبلغ (ریال)')
    authority = models.CharField(max_length=255, blank=True, null=True, verbose_name='کد مرجع', db_index=True)
    ref_id = models.CharField(max_length=255, blank=True, null=True, verbose_name='شماره پیگیری', db_index=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending', verbose_name='وضعیت', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد', db_index=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')
    
    def __str__(self):
        return f"Payment for {self.sample_work.title} - {self.get_status_display()}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'پرداخت'
        verbose_name_plural = 'پرداخت‌ها'
        indexes = [
            models.Index(fields=['sample_work', 'status']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['authority']),
        ]


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
    
    sample_work = models.ForeignKey(SampleWork, on_delete=models.CASCADE, verbose_name='نمونه کار', db_index=True)
    duration = models.IntegerField(verbose_name='مدت زمان (روز)')
    status = models.CharField(max_length=20, choices=ADDON_STATUS_CHOICES, default='pending', verbose_name='وضعیت', db_index=True)
    addon_id = models.CharField(max_length=255, blank=True, null=True, verbose_name='شناسه افزونه', db_index=True)
    error_message = models.TextField(blank=True, null=True, verbose_name='پیام خطا')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد', db_index=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')
    
    def __str__(self):
        return f"Addon for {self.sample_work.title} - {self.get_status_display()}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'افزونه پست'
        verbose_name_plural = 'افزونه‌های پست'
        indexes = [
            models.Index(fields=['sample_work', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]
