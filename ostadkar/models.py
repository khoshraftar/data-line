from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Create your models here.

class UserAuth(models.Model):
    user_id = models.CharField(max_length=255, unique=True)
    access_token = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"User {self.user_id}"

class SampleWork(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    main_image = models.ImageField(upload_to='sample_works/')
    additional_images = models.TextField(help_text="List of image URLs with descriptions (one per line, format: URL|Description)")
    user = models.ForeignKey(UserAuth, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']

    def get_additional_images(self):
        """Parse additional_images field into a list of dictionaries"""
        if not self.additional_images:
            return []
        
        images = []
        for line in self.additional_images.strip().split('\n'):
            if '|' in line:
                url, description = line.split('|', 1)
                images.append({
                    'url': url.strip(),
                    'description': description.strip()
                })
        return images

class SampleWorkImage(models.Model):
    sample_work = models.ForeignKey(SampleWork, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='sample_works/images/')
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.sample_work.title}"

    class Meta:
        ordering = ['created_at']

class PostImage(models.Model):
    post_token = models.CharField(max_length=255)
    description = models.TextField()
    images = models.TextField(help_text="Enter image URLs (one per line)")
    user = models.ForeignKey(UserAuth, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Images for post {self.post_token}"

    def get_images_list(self):
        """Return list of image URLs"""
        return [url.strip() for url in self.images.split('\n') if url.strip()]

    class Meta:
        ordering = ['-created_at']
