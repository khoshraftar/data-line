from django.contrib import admin
from .models import UserAuth, SampleWork, PostImage, Payment

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
