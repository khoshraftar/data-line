from django.db import models
from django.utils import timezone

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


class Payment(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'در انتظار پرداخت'),
        ('completed', 'پرداخت شده'),
        ('failed', 'ناموفق'),
        ('cancelled', 'لغو شده'),
    ]
    
    user_auth = models.ForeignKey(UserAuth, on_delete=models.CASCADE, verbose_name='کاربر', db_index=True)
    amount = models.IntegerField(verbose_name='مبلغ (ریال)')
    authority = models.CharField(max_length=255, blank=True, null=True, verbose_name='کد مرجع', db_index=True)
    ref_id = models.CharField(max_length=255, blank=True, null=True, verbose_name='شماره پیگیری', db_index=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending', verbose_name='وضعیت', db_index=True)
    subscription_start = models.DateTimeField(blank=True, null=True, verbose_name='شروع اشتراک')
    subscription_end = models.DateTimeField(blank=True, null=True, verbose_name='پایان اشتراک')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد', db_index=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')
    
    def __str__(self):
        return f"Payment for {self.user_auth.user_id} - {self.get_status_display()}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'پرداخت'
        verbose_name_plural = 'پرداخت‌ها'
        indexes = [
            models.Index(fields=['user_auth', 'status']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['authority']),
        ]


class Conversation(models.Model):
    """Model to store chatbot conversations"""
    user_auth = models.ForeignKey(UserAuth, on_delete=models.CASCADE, verbose_name='کاربر')
    conversation_id = models.CharField(max_length=255, unique=True, verbose_name='شناسه مکالمه', db_index=True)
    title = models.CharField(max_length=500, blank=True, null=True, verbose_name='عنوان مکالمه')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد', db_index=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')

    def __str__(self):
        return f"Conversation {self.conversation_id} - {self.title or 'No title'}"

    class Meta:
        verbose_name = 'مکالمه'
        verbose_name_plural = 'مکالمات'


class Message(models.Model):
    """Model to store individual messages in conversations"""
    MESSAGE_TYPES = [
        ('user', 'کاربر'),
        ('bot', 'ربات'),
    ]

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages', verbose_name='مکالمه')
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, verbose_name='نوع پیام')
    content = models.TextField(verbose_name='محتوای پیام')
    metadata = models.JSONField(default=dict, blank=True, verbose_name='متادیتا')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد', db_index=True)

    def __str__(self):
        return f"{self.get_message_type_display()} - {self.content[:50]}..."

    class Meta:
        verbose_name = 'پیام'
        verbose_name_plural = 'پیام‌ها'
        ordering = ['created_at']
