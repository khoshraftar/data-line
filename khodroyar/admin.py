from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from datetime import timedelta
from .models import UserAuth, Conversation, Message, Payment

# Register your models here.

@admin.register(UserAuth)
class UserAuthAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'phone', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['user_id', 'phone']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['conversation_id', 'user_auth', 'title', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at', 'updated_at']
    search_fields = ['conversation_id', 'title', 'user_auth__user_id']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['conversation', 'message_type', 'content_preview', 'created_at']
    list_filter = ['message_type', 'created_at']
    search_fields = ['content', 'conversation__conversation_id']
    readonly_fields = ['created_at']
    
    def content_preview(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_preview.short_description = 'محتوای پیام'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'user_auth', 
        'plan_name', 
        'formatted_amount', 
        'subscription_status', 
        'subscription_duration', 
        'status', 
        'created_at'
    ]
    list_filter = ['status', 'created_at', 'subscription_start', 'subscription_end']
    search_fields = ['user_auth__user_id', 'user_auth__phone', 'authority', 'ref_id']
    readonly_fields = ['created_at', 'updated_at', 'subscription_status_display']
    list_editable = ['status']
    actions = ['extend_subscription_1_day', 'extend_subscription_7_days', 'mark_as_completed', 'mark_as_failed']
    
    fieldsets = (
        ('اطلاعات کاربر', {
            'fields': ('user_auth',)
        }),
        ('اطلاعات پرداخت', {
            'fields': ('amount', 'status', 'formatted_amount')
        }),
        ('اطلاعات اشتراک', {
            'fields': ('plan_name', 'subscription_start', 'subscription_end', 'subscription_duration', 'subscription_status_display')
        }),
        ('اطلاعات ZarinPal', {
            'fields': ('authority', 'ref_id'),
            'classes': ('collapse',)
        }),
        ('متادیتا', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
