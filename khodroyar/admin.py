from django.contrib import admin
from .models import UserAuth

# Register your models here.
@admin.register(UserAuth)
class UserAuthAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'phone', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['user_id', 'phone']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('اطلاعات کاربر', {
            'fields': ('user_id', 'phone')
        }),
        ('توکن', {
            'fields': ('access_token',),
            'classes': ('collapse',)
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
