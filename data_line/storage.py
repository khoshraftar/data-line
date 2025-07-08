from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings

class MediaStorage(S3Boto3Storage):
    location = getattr(settings, 'AWS_S3_MEDIA_LOCATION', 'media')
    default_acl = 'public-read'
    file_overwrite = False
    querystring_auth = False
    custom_domain = getattr(settings, 'AWS_S3_CUSTOM_DOMAIN', None) 