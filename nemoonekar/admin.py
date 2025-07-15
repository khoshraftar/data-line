from django.contrib import admin
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html
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
        return Payment.objects.filter(sample_work__user=obj).count()
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
                Payment.objects.filter(sample_work__user=user).count()
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
    list_display = ['title', 'post_token', 'user', 'is_reviewed', 'is_archived', 'images_count', 'addons_count', 'created_at']
    list_filter = ['is_reviewed', 'is_archived', 'created_at']
    list_editable = ['is_reviewed']
    search_fields = ['title', 'post_token', 'user__user_id', 'user__phone']
    readonly_fields = ['uuid', 'created_at', 'archived_at']
    ordering = ['-created_at']
    actions = ['mark_as_reviewed', 'mark_as_unreviewed', 'archive_sample_works', 'unarchive_sample_works']
    
    fieldsets = (
        ('اطلاعات نمونه کار', {
            'fields': ('title', 'post_token', 'user', 'description')
        }),
        ('وضعیت بررسی', {
            'fields': ('is_reviewed',)
        }),
        ('وضعیت آرشیو', {
            'fields': ('is_archived', 'archived_at'),
            'classes': ('collapse',)
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
    
    def get_queryset(self, request):
        """Show all sample works including archived ones in admin"""
        return SampleWork.all_including_archived()
    
    def images_count(self, obj):
        return obj.postimage_set.count()
    images_count.short_description = 'تعداد تصاویر'
    
    def addons_count(self, obj):
        return obj.postaddon_set.count()
    addons_count.short_description = 'تعداد افزونه‌ها'
    
    def mark_as_reviewed(self, request, queryset):
        """Mark selected sample works as reviewed"""
        updated = queryset.update(is_reviewed=True)
        self.message_user(request, f'{updated} نمونه کار به عنوان بررسی شده علامت‌گذاری شد.')
    mark_as_reviewed.short_description = "علامت‌گذاری به عنوان بررسی شده"
    
    def mark_as_unreviewed(self, request, queryset):
        """Mark selected sample works as unreviewed"""
        updated = queryset.update(is_reviewed=False)
        self.message_user(request, f'{updated} نمونه کار به عنوان بررسی نشده علامت‌گذاری شد.')
    mark_as_unreviewed.short_description = "علامت‌گذاری به عنوان بررسی نشده"
    
    def archive_sample_works(self, request, queryset):
        """Archive selected sample works"""
        archived_count = 0
        for sample_work in queryset:
            if not sample_work.is_archived:
                sample_work.archive()
                archived_count += 1
        
        if archived_count > 0:
            self.message_user(request, f'{archived_count} نمونه کار آرشیو شد.')
        else:
            self.message_user(request, 'هیچ نمونه کار جدیدی آرشیو نشد.')
    archive_sample_works.short_description = "آرشیو نمونه کارهای انتخاب شده"
    
    def unarchive_sample_works(self, request, queryset):
        """Unarchive selected sample works"""
        unarchived_count = 0
        for sample_work in queryset:
            if sample_work.is_archived:
                sample_work.unarchive()
                unarchived_count += 1
        
        if unarchived_count > 0:
            self.message_user(request, f'{unarchived_count} نمونه کار از آرشیو خارج شد.')
        else:
            self.message_user(request, 'هیچ نمونه کار جدیدی از آرشیو خارج نشد.')
    unarchive_sample_works.short_description = "خارج کردن نمونه کارهای انتخاب شده از آرشیو"

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

# Import the review admin
from . import admin_review
