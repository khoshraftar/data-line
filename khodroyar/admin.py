from django.contrib import admin
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
    list_display = ['user_auth', 'amount', 'status', 'authority', 'ref_id', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user_auth__user_id', 'authority', 'ref_id']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('اطلاعات پرداخت', {
            'fields': ('user_auth', 'amount', 'status')
        }),
        ('اطلاعات ZarinPal', {
            'fields': ('authority', 'ref_id')
        }),
        ('اطلاعات اشتراک', {
            'fields': ('subscription_start', 'subscription_end'),
            'classes': ('collapse',)
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
