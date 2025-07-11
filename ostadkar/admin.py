from django.contrib import admin
from .models import UserAuth, SampleWork, PostImage, Payment, PostAddon

# Register your models here.

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['sample_work', 'amount', 'status', 'authority', 'ref_id', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['sample_work__title', 'authority', 'ref_id']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('اطلاعات پرداخت', {
            'fields': ('sample_work', 'amount', 'status')
        }),
        ('اطلاعات ZarinPal', {
            'fields': ('authority', 'ref_id')
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(PostAddon)
class PostAddonAdmin(admin.ModelAdmin):
    list_display = ['sample_work', 'status', 'addon_id', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['sample_work__title', 'addon_id', 'payment__ref_id']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('اطلاعات افزونه', {
            'fields': ('sample_work', 'duration', 'status')
        }),
        ('اطلاعات Divar', {
            'fields': ('addon_id', 'error_message')
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
