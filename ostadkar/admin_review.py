from django.contrib import admin
from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from .models import SampleWork, PostImage, Payment, PostAddon

# Create a custom admin site for review functionality
class SampleWorkReviewSite(admin.AdminSite):
    site_header = "بررسی نمونه کارها"
    site_title = "بررسی نمونه کارها"
    index_title = "پنل بررسی"
    
    def index(self, request, extra_context=None):
        """Custom index view for the review admin site"""
        unreviewed_count = SampleWork.objects.filter(is_reviewed=False).count()
        reviewed_count = SampleWork.objects.filter(is_reviewed=True).count()
        total_count = SampleWork.objects.count()
        
        extra_context = extra_context or {}
        extra_context.update({
            'unreviewed_count': unreviewed_count,
            'reviewed_count': reviewed_count,
            'total_count': total_count,
        })
        
        return super().index(request, extra_context)

# Create the review admin site instance
review_site = SampleWorkReviewSite(name='samplework_review')

class SampleWorkReviewAdmin(admin.ModelAdmin):
    model = SampleWork
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('', self.admin_site.admin_view(self.review_sample_work), name='samplework_review'),
            path('<uuid:sample_work_id>/', self.admin_site.admin_view(self.review_sample_work_detail), name='samplework_review_detail'),
            path('<uuid:sample_work_id>/accept/', self.admin_site.admin_view(self.accept_sample_work), name='samplework_accept'),
            path('<uuid:sample_work_id>/reject/', self.admin_site.admin_view(self.reject_sample_work), name='samplework_reject'),
        ]
        return custom_urls + urls
    
    def review_sample_work(self, request):
        """Show the first unreviewed sample work"""
        unreviewed_work = SampleWork.objects.filter(is_reviewed=False).first()
        if unreviewed_work:
            return HttpResponseRedirect(
                reverse('samplework_review:samplework_review_detail', args=[unreviewed_work.uuid])
            )
        else:
            messages.info(request, 'هیچ نمونه کار بررسی نشده‌ای وجود ندارد.')
            return HttpResponseRedirect(reverse('admin:ostadkar_samplework_changelist'))
    
    def review_sample_work_detail(self, request, sample_work_id):
        """Show detailed view of a sample work for review"""
        sample_work = get_object_or_404(SampleWork, uuid=sample_work_id)
        images = PostImage.objects.filter(sample_work=sample_work)
        payments = Payment.objects.filter(sample_work=sample_work)
        addons = PostAddon.objects.filter(sample_work=sample_work)
        
        context = {
            'title': f'بررسی نمونه کار: {sample_work.title}',
            'sample_work': sample_work,
            'images': images,
            'payments': payments,
            'addons': addons,
            'opts': self.model._meta,
            'has_change_permission': self.has_change_permission(request),
        }
        return render(request, 'admin/ostadkar/samplework/review_detail.html', context)
    
    def accept_sample_work(self, request, sample_work_id):
        """Accept and mark sample work as reviewed"""
        sample_work = get_object_or_404(SampleWork, uuid=sample_work_id)
        sample_work.is_reviewed = True
        sample_work.save()
        messages.success(request, f'نمونه کار "{sample_work.title}" پذیرفته و بررسی شد.')
        return HttpResponseRedirect('/admin/review/')
    
    def reject_sample_work(self, request, sample_work_id):
        """Reject and delete sample work"""
        sample_work = get_object_or_404(SampleWork, uuid=sample_work_id)
        title = sample_work.title
        sample_work.delete()
        messages.success(request, f'نمونه کار "{title}" رد و حذف شد.')
        return HttpResponseRedirect('/admin/review/')

# Register the review admin view with the review site
review_site.register(SampleWork, SampleWorkReviewAdmin)

# Set the template directory for the review site
review_site.site_url = '/admin/review/' 