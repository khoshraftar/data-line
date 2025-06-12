from django import forms
from .models import SampleWork, SampleWorkImage, PostImage

class SampleWorkForm(forms.ModelForm):
    class Meta:
        model = SampleWork
        fields = ['title', 'description', 'main_image', 'additional_images']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'additional_images': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Enter image URLs with descriptions (one per line)\nFormat: URL|Description\nExample: https://example.com/image1.jpg|Description of image 1'
            }),
        }

class SampleWorkImageForm(forms.ModelForm):
    class Meta:
        model = SampleWorkImage
        fields = ['image', 'description']

SampleWorkImageFormSet = forms.inlineformset_factory(
    SampleWork,
    SampleWorkImage,
    form=SampleWorkImageForm,
    extra=3,  # Number of empty forms to display
    can_delete=True
)

class PostImageForm(forms.ModelForm):
    class Meta:
        model = PostImage
        fields = ['description', 'images']
        widgets = {
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter a general description for all images'
            }),
            'images': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Enter image URLs (one per line)'
            })
        } 