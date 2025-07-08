from django import forms
from .models import PostImage, SampleWork

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True
    
    def __init__(self, attrs=None):
        default_attrs = {
            'accept': 'image/*',
            'capture': None,  # This allows both camera and gallery
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
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result

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
        help_text='می‌توانید چندین تصویر را همزمان انتخاب کنید. برای انتخاب از گالری، روی "انتخاب فایل" کلیک کنید.',
        label='تصاویر'
    )
    description = forms.CharField(
        label='توضیحات تصاویر',
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'placeholder': 'توضیحات مربوط به این تصاویر را وارد کنید', 
            'rows': 3,
            'dir': 'rtl'
        }),
        required=False
    )

