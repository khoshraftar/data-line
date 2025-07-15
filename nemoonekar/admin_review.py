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
        archived_count = SampleWork.archived().count()
        total_count = SampleWork.all_including_archived().count()
        
        extra_context = extra_context or {}
        extra_context.update({
            'unreviewed_count': unreviewed_count,
            'reviewed_count': reviewed_count,
            'archived_count': archived_count,
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
            path('accept/', self.admin_site.admin_view(self.accept_sample_work), name='samplework_accept'),
            path('reject/', self.admin_site.admin_view(self.reject_sample_work), name='samplework_reject'),
        ]
        return custom_urls + urls
    
    def review_sample_work(self, request):
        """Show the first unreviewed sample work"""
        sample_work = SampleWork.objects.filter(is_reviewed=False).first()
        if sample_work:
            return self.show_sample_work_detail(request, sample_work)
        else:
            messages.info(request, 'هیچ نمونه کار بررسی نشده‌ای وجود ندارد.')
            return HttpResponseRedirect(reverse('admin:nemoonekar_samplework_changelist'))
    
    def show_sample_work_detail(self, request, sample_work):
        """Show detailed view of a sample work for review"""
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
        return render(request, 'admin/nemoonekar/samplework/review_detail.html', context)
    
    def accept_sample_work(self, request):
        """Accept and mark sample work as reviewed, then reload page"""
        sample_work = SampleWork.objects.filter(is_reviewed=False).first()
        if not sample_work:
            messages.error(request, 'نمونه کار مورد نظر یافت نشد.')
            return HttpResponseRedirect('/admin/review/')
        
        title = sample_work.title
        sample_work.is_reviewed = True
        sample_work.save()
        
        messages.success(request, f'نمونه کار "{title}" پذیرفته و بررسی شد.')
        return HttpResponseRedirect('/admin/review/nemoonekar/samplework/')
    
    def reject_sample_work(self, request):
        """Reject and archive sample work, then reload page"""
        sample_work = SampleWork.objects.filter(is_reviewed=False).first()
        if not sample_work:
            messages.error(request, 'نمونه کار مورد نظر یافت نشد.')
            return HttpResponseRedirect('/admin/review/')
        
        title = sample_work.title
        sample_work.is_reviewed = True  # Mark as reviewed
        sample_work.save()  # Save the reviewed status
        sample_work.archive()  # Then archive it
        
        messages.success(request, f'نمونه کار "{title}" رد و آرشیو شد.')
        return HttpResponseRedirect('/admin/review/nemoonekar/samplework/')

# Register the review admin view with the review site
review_site.register(SampleWork, SampleWorkReviewAdmin)

# Set the template directory for the review site
review_site.site_url = '/admin/review/' 