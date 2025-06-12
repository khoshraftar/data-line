from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid

# Create your models here.

class UserAuth(models.Model):
    user_id = models.CharField(max_length=255, unique=True)
    access_token = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"User {self.user_id}"


class SampleWork(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    title = models.CharField(max_length=200)
    post_token = models.CharField(max_length=8)
    user = models.ForeignKey(UserAuth, on_delete=models.CASCADE)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.sample_work.title}"

    class Meta:
        ordering = ['created_at']

class PostImage(models.Model):
    image = models.ImageField(upload_to='sample_works/images/')
    created_at = models.DateTimeField(auto_now_add=True)
    sample_work = models.ForeignKey(SampleWork, on_delete=models.CASCADE)

    def __str__(self):
        return f"Image for {self.sample_work.title}"

    class Meta:
        ordering = ['-created_at']
