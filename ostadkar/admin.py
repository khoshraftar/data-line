from django.contrib import admin
from .models import UserAuth, SampleWork, PostImage, Payment, PostAddon

# Register your models here.

class SampleWorkInline(admin.TabularInline):
    model = SampleWork
    extra = 0
    readonly_fields = ['uuid', 'created_at']
    fields = ['title', 'post_token', 'created_at']
    can_delete = False

class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ['created_at', 'updated_at']
    fields = ['sample_work', 'amount', 'status', 'created_at']
    can_delete = False

class PostImageInline(admin.TabularInline):
    model = PostImage
    extra = 0
    readonly_fields = ['created_at']
    fields = ['image', 'created_at']
    can_delete = False

class PostAddonInline(admin.TabularInline):
    model = PostAddon
    extra = 0
    readonly_fields = ['created_at', 'updated_at']
    fields = ['duration', 'status', 'addon_id', 'created_at']
    can_delete = False

@admin.register(UserAuth)
class UserAuthAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'phone', 'sample_works_count', 'payments_count', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['user_id', 'phone']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    actions = ['export_user_data', 'mark_users_active']
    
    fieldsets = (
        ('اطلاعات کاربر', {
            'fields': ('user_id', 'phone')
        }),
        ('اطلاعات OAuth', {
            'fields': ('access_token',),
            'classes': ('collapse',)
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [SampleWorkInline]
    
    def sample_works_count(self, obj):
        return obj.samplework_set.count()
    sample_works_count.short_description = 'تعداد نمونه کارها'
    
    def payments_count(self, obj):
        return obj.payment_set.count()
    payments_count.short_description = 'تعداد پرداخت‌ها'
    
    def export_user_data(self, request, queryset):
        """Export selected users' data"""
        from django.http import HttpResponse
        import csv
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="oauth_users.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['User ID', 'Phone', 'Created At', 'Updated At', 'Sample Works Count', 'Payments Count'])
        
        for user in queryset:
            writer.writerow([
                user.user_id,
                user.phone or '',
                user.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                user.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                user.samplework_set.count(),
                user.payment_set.count()
            ])
        
        return response
    export_user_data.short_description = "Export selected users' data to CSV"
    
    def mark_users_active(self, request, queryset):
        """Mark selected users as active (placeholder for future functionality)"""
        count = queryset.count()
        self.message_user(request, f'{count} users marked as active.')
    mark_users_active.short_description = "Mark selected users as active"

@admin.register(SampleWork)
class SampleWorkAdmin(admin.ModelAdmin):
    list_display = ['title', 'post_token', 'user', 'images_count', 'addons_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['title', 'post_token', 'user__user_id', 'user__phone']
    readonly_fields = ['uuid', 'created_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('اطلاعات نمونه کار', {
            'fields': ('title', 'post_token', 'user', 'description')
        }),
        ('اطلاعات فنی', {
            'fields': ('uuid',),
            'classes': ('collapse',)
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [PostImageInline, PostAddonInline]
    
    def images_count(self, obj):
        return obj.postimage_set.count()
    images_count.short_description = 'تعداد تصاویر'
    
    def addons_count(self, obj):
        return obj.postaddon_set.count()
    addons_count.short_description = 'تعداد افزونه‌ها'

@admin.register(PostImage)
class PostImageAdmin(admin.ModelAdmin):
    list_display = ['sample_work', 'image', 'created_at']
    list_filter = ['created_at']
    search_fields = ['sample_work__title']
    readonly_fields = ['created_at']
    ordering = ['-created_at']

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

# Customize admin site
admin.site.site_header = "دیتا لاین - مدیریت سیستم"
admin.site.site_title = "دیتا لاین"
admin.site.index_title = "پنل مدیریت"

# Customize admin ordering
admin.site.site_url = '/'

# Add custom CSS for better RTL support
class Media:
    css = {
        'all': ('admin/css/rtl.css',)
    }
