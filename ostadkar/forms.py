from django import forms
from .models import PostImage, SampleWork

class SampleWorkForm(forms.ModelForm):
    class Meta:
        model = SampleWork
        fields = ['title', 'description']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter the title of the sample work'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter a description for the sample work'
            })
        }


class MultiImageUploadForm(forms.Form):
    images = forms.ImageField(widget=forms.ClearableFileInput(attrs={'multiple': True}))

