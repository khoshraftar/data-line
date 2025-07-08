from django import forms
from django.core.exceptions import ValidationError
from .models import PostImage, SampleWork
import os

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True
    
    def __init__(self, attrs=None):
        default_attrs = {
            'accept': 'image/*',
            'multiple': True,
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            # Limit to 24 images
            if len(data) > 24:
                raise ValidationError('حداکثر ۲۴ تصویر می‌توانید آپلود کنید.')
            
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result

    def validate(self, value):
        super().validate(value)
        
        if isinstance(value, (list, tuple)):
            for file in value:
                self._validate_file(file)
        elif value:
            self._validate_file(value)
    
    def _validate_file(self, file):
        # Check file size (2.5MB limit)
        if file.size > 2621440:  # 2.5MB in bytes
            raise ValidationError(f'حجم فایل {file.name} بیش از ۲.۵ مگابایت است.')
        
        # Check file extension
        allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg']
        file_extension = os.path.splitext(file.name)[1].lower().lstrip('.')
        
        if file_extension not in allowed_extensions:
            raise ValidationError(f'فرمت فایل {file.name} پشتیبانی نمی‌شود. فرمت‌های مجاز: {", ".join(allowed_extensions)}')

class SampleWorkForm(forms.ModelForm):
    class Meta:
        model = SampleWork
        fields = ['title', 'description']
        labels = {
            'title': 'عنوان نمونه کار',
            'description': 'توضیحات نمونه کار',
        }
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'عنوان نمونه کار خود را وارد کنید',
                'dir': 'rtl'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 
                'placeholder': 'توضیحات نمونه کار خود را وارد کنید', 
                'rows': 4,
                'dir': 'rtl'
            }),
        }


class SampleWorkImageForm(forms.Form):
    images = MultipleFileField(
        required=True,
        help_text='می‌توانید حداکثر ۲۴ تصویر را همزمان انتخاب کنید. حجم هر فایل نباید بیش از ۲.۵ مگابایت باشد.',
        label='تصاویر'
    )

