from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings

class MediaStorage(S3Boto3Storage):
    """S3 storage for media files only"""
    location = getattr(settings, 'AWS_S3_MEDIA_LOCATION', 'media')
    default_acl = 'public-read'
    file_overwrite = False
    querystring_auth = False
    custom_domain = getattr(settings, 'AWS_S3_CUSTOM_DOMAIN', None)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure we're using S3 storage
        if not self.bucket_name:
            raise ValueError("AWS_STORAGE_BUCKET_NAME must be set for S3 storage") 