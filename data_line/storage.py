from storages.backends.s3boto3 import S3Boto3Storage
import os

class MediaStorage(S3Boto3Storage):
    location = os.getenv('AWS_S3_MEDIA_LOCATION', 'media')
    default_acl = 'public-read'
    file_overwrite = False 