from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class SampleWork(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sample_works')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='sample_works/')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}'s work - {self.title}"
