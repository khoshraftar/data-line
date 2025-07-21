from django.contrib import admin
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.shortcuts import render, get_object_or_404
from django import forms
from django.utils.html import format_html
from .models import UserAuth, Conversation, Message, Payment
from .views import send_welcome_message_after_payment, send_bot_message
from .utils import to_shamsi_datetime_full
from datetime import datetime

# Register your models here.

class WelcomeMessageForm(forms.Form):
    message = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 5, 'cols': 80}),
        label='پیام خوش‌آمدگویی',
        initial="""🎉 تبریک! اشتراک خودرویار شما با موفقیت فعال شد!

✅ پرداخت شما تایید شد
💰 مبلغ: {amount:,} ریال
📅 شروع اشتراک: {start_date}
📅 پایان اشتراک: {end_date}
🔢 شماره پیگیری: {ref_id}

🚗 حالا می‌توانید از خدمات خودرویار استفاده کنید:
• جستجوی خودرو
• اطلاعات قیمت
• مقایسه خودروها
• راهنمای خرید

برای شروع، پیام خود را بنویسید! (مثلا: سلام)""",
        help_text='پیام خوش‌آمدگویی که برای کاربر ارسال خواهد شد'
    )


class SendMessageForm(forms.Form):
    message = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 5, 'cols': 80}),
        label='پیام',
        help_text='پیامی که برای کاربر ارسال خواهد شد'
    )

@admin.register(UserAuth)
class UserAuthAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'phone', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['user_id', 'phone']
    readonly_fields = ['created_at', 'updated_at']
    
    actions = ['send_welcome_message']
    
    def send_welcome_message(self, request, queryset):
        """Send welcome message to selected users"""
        if 'apply' in request.POST:
            form = WelcomeMessageForm(request.POST)
            if form.is_valid():
                message_template = form.cleaned_data['message']
                success_count = 0
                error_count = 0
                
                for user_auth in queryset:
                    try:
                        # Get user's latest completed payment for formatting
                        latest_payment = Payment.objects.filter(
                            user_auth=user_auth,
                            status='completed'
                        ).order_by('-created_at').first()
                        
                        # Format message with payment data or use placeholders
                        if latest_payment:
                            formatted_message = message_template.format(
                                amount=latest_payment.amount,
                                start_date=to_shamsi_datetime_full(latest_payment.subscription_start) if latest_payment.subscription_start else "نامشخص",
                                end_date=to_shamsi_datetime_full(latest_payment.subscription_end) if latest_payment.subscription_end else "نامشخص",
                                ref_id=latest_payment.ref_id or "نامشخص"
                            )
                        else:
                            # Use placeholder values if no payment exists
                            formatted_message = message_template.format(
                                amount=0,
                                start_date="نامشخص",
                                end_date="نامشخص",
                                ref_id="ADMIN_WELCOME"
                            )
                        
                        # Create a mock payment object for the welcome message function
                        class MockPayment:
                            def __init__(self, user_auth, message):
                                self.user_auth = user_auth
                                self.amount = latest_payment.amount if latest_payment else 0
                                self.ref_id = latest_payment.ref_id if latest_payment else 'ADMIN_WELCOME'
                                self.subscription_start = latest_payment.subscription_start if latest_payment else None
                                self.subscription_end = latest_payment.subscription_end if latest_payment else None
                        
                        mock_payment = MockPayment(user_auth, formatted_message)
                        
                        # Send welcome message
                        if send_welcome_message_after_payment(user_auth, mock_payment):
                            success_count += 1
                        else:
                            error_count += 1
                    except Exception as e:
                        error_count += 1
                        print(f"Error sending welcome message to {user_auth.user_id}: {str(e)}")
                
                if success_count > 0:
                    self.message_user(
                        request,
                        f'پیام خوش‌آمدگویی با موفقیت برای {success_count} کاربر ارسال شد.',
                        messages.SUCCESS
                    )
                
                if error_count > 0:
                    self.message_user(
                        request,
                        f'خطا در ارسال پیام برای {error_count} کاربر.',
                        messages.ERROR
                    )
                
                return HttpResponseRedirect(request.get_full_path())
        else:
            form = WelcomeMessageForm()
        
        context = {
            'title': 'ارسال پیام خوش‌آمدگویی',
            'form': form,
            'queryset': queryset,
            'opts': self.model._meta,
            'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
        }
        
        return render(request, 'admin/khodroyar/userauth/send_welcome_message.html', context)
    
    send_welcome_message.short_description = 'ارسال پیام خوش‌آمدگویی به کاربران انتخاب شده'


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['conversation_id', 'user_auth', 'title', 'is_active', 'created_at', 'view_conversation_link']
    list_filter = ['is_active', 'created_at', 'updated_at']
    search_fields = ['conversation_id', 'title', 'user_auth__user_id']
    readonly_fields = ['created_at', 'updated_at']
    
    actions = ['view_conversation', 'send_message']
    
    def view_conversation_link(self, obj):
        """Create links to view the conversation and send message"""
        view_url = reverse('admin:khodroyar_conversation_view', args=[obj.id])
        send_url = reverse('admin:khodroyar_conversation_send_message', args=[obj.id])
        return format_html(
            '<a href="{}" class="button" style="margin-right: 5px;">👁️ مشاهده</a>'
            '<a href="{}" class="button" style="background: #28a745; color: white;">📤 ارسال پیام</a>',
            view_url, send_url
        )
    view_conversation_link.short_description = 'عملیات'
    view_conversation_link.allow_tags = True
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:conversation_id>/view/',
                self.admin_site.admin_view(self.view_conversation_detail),
                name='khodroyar_conversation_view',
            ),
            path(
                '<int:conversation_id>/send-message/',
                self.admin_site.admin_view(self.send_message_to_conversation),
                name='khodroyar_conversation_send_message',
            ),
        ]
        return custom_urls + urls
    
    def view_conversation(self, request, queryset):
        """View conversation action - redirects to the first selected conversation"""
        if queryset.count() != 1:
            self.message_user(
                request,
                'لطفاً دقیقاً یک مکالمه را انتخاب کنید.',
                messages.ERROR
            )
            return HttpResponseRedirect(request.get_full_path())
        
        conversation = queryset.first()
        return HttpResponseRedirect(
            reverse('admin:khodroyar_conversation_view', args=[conversation.id])
        )
    
    view_conversation.short_description = 'مشاهده مکالمه انتخاب شده'
    
    def send_message(self, request, queryset):
        """Send a message to selected conversations"""
        if 'apply' in request.POST:
            form = SendMessageForm(request.POST)
            if form.is_valid():
                message_content = form.cleaned_data['message']
                success_count = 0
                error_count = 0
                
                for conversation in queryset:
                    try:
                        # Send message using the conversation's user_auth and conversation_id
                        if send_bot_message(conversation.user_auth, conversation.conversation_id, message_content):
                            # Also save the message to our database
                            Message.objects.create(
                                conversation=conversation,
                                message_type='bot',
                                content=message_content,
                                metadata={
                                    'sent_at': datetime.now().isoformat(),
                                    'timestamp': datetime.now().isoformat(),
                                    'admin_sent': True
                                }
                            )
                            success_count += 1
                        else:
                            error_count += 1
                    except Exception as e:
                        error_count += 1
                        print(f"Error sending message to {conversation.conversation_id}: {str(e)}")
                
                if success_count > 0:
                    self.message_user(
                        request,
                        f'پیام با موفقیت برای {success_count} مکالمه ارسال شد.',
                        messages.SUCCESS
                    )
                
                if error_count > 0:
                    self.message_user(
                        request,
                        f'خطا در ارسال پیام برای {error_count} مکالمه.',
                        messages.ERROR
                    )
                
                return HttpResponseRedirect(request.get_full_path())
        else:
            form = SendMessageForm()
        
        context = {
            'title': 'ارسال پیام به مکالمه‌ها',
            'form': form,
            'queryset': queryset,
            'opts': self.model._meta,
            'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
        }
        
        return render(request, 'admin/khodroyar/conversation/send_message.html', context)
    
    send_message.short_description = 'ارسال پیام به مکالمه‌ها انتخاب شده'
    
    def send_message_to_conversation(self, request, conversation_id):
        """Send a message to a specific conversation"""
        conversation = get_object_or_404(Conversation, id=conversation_id)
        
        if 'apply' in request.POST:
            form = SendMessageForm(request.POST)
            if form.is_valid():
                message_content = form.cleaned_data['message']
                try:
                    # Send message using the conversation's user_auth and conversation_id
                    if send_bot_message(conversation.user_auth, conversation.conversation_id, message_content):
                        # Also save the message to our database
                        Message.objects.create(
                            conversation=conversation,
                            message_type='bot',
                            content=message_content,
                            metadata={
                                'sent_at': datetime.now().isoformat(),
                                'timestamp': datetime.now().isoformat(),
                                'admin_sent': True
                            }
                        )
                        self.message_user(
                            request,
                            f'پیام با موفقیت به مکالمه {conversation.conversation_id} ارسال شد.',
                            messages.SUCCESS
                        )
                    else:
                        self.message_user(
                            request,
                            f'خطا در ارسال پیام به مکالمه {conversation.conversation_id}.',
                            messages.ERROR
                        )
                except Exception as e:
                    self.message_user(
                        request,
                        f'خطا در ارسال پیام: {str(e)}',
                        messages.ERROR
                    )
                
                return HttpResponseRedirect(
                    reverse('admin:khodroyar_conversation_view', args=[conversation.id])
                )
        else:
            form = SendMessageForm()
        
        context = {
            'title': f'ارسال پیام به مکالمه: {conversation.title or conversation.conversation_id}',
            'form': form,
            'conversation': conversation,
            'opts': self.model._meta,
        }
        
        return render(request, 'admin/khodroyar/conversation/send_message_single.html', context)
    
    def view_conversation_detail(self, request, conversation_id):
        """Display conversation detail with all messages"""
        conversation = get_object_or_404(Conversation, id=conversation_id)
        messages = conversation.messages.all().order_by('created_at')
        
        # Calculate message statistics
        total_messages = messages.count()
        user_messages = messages.filter(message_type='user').count()
        bot_messages = messages.filter(message_type='bot').count()
        
        context = {
            'title': f'مشاهده مکالمه: {conversation.title or conversation.conversation_id}',
            'conversation': conversation,
            'messages': messages,
            'total_messages': total_messages,
            'user_messages': user_messages,
            'bot_messages': bot_messages,
            'opts': self.model._meta,
        }
        
        return render(request, 'admin/khodroyar/conversation/view_conversation.html', context)


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
