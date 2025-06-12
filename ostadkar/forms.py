from django import forms
from .models import SampleWork

class SampleWorkForm(forms.ModelForm):
    class Meta:
        model = SampleWork
        fields = ['title', 'description', 'image']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        } 