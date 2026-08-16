"""Stockage des vidéos de cours (local privé ou S3-compatible : Cloudflare R2, B2, Wasabi…)."""
from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage


COURS_VIDEO_URL_PREFIX = '/mon-espace/videos-cours/'


def cloud_media_configured() -> bool:
    return bool(
        getattr(settings, 'AWS_STORAGE_BUCKET_NAME', '')
        and getattr(settings, 'AWS_ACCESS_KEY_ID', '')
        and getattr(settings, 'AWS_SECRET_ACCESS_KEY', '')
    )


def cours_video_local_root() -> Path:
    root = Path(getattr(settings, 'PRIVATE_MEDIA_ROOT', settings.BASE_DIR / 'private_media'))
    return root / getattr(settings, 'COURS_VIDEO_LOCATION', 'cours_videos')


def get_cours_video_storage():
    """Storage dédié aux vidéos de cours (privé + URL signée si cloud)."""
    if cloud_media_configured():
        from storages.backends.s3boto3 import S3Boto3Storage

        class CoursVideoS3Storage(S3Boto3Storage):
            location = getattr(settings, 'COURS_VIDEO_LOCATION', 'cours_videos')
            default_acl = 'private'
            file_overwrite = False
            querystring_auth = True
            querystring_expire = int(getattr(settings, 'AWS_QUERYSTRING_EXPIRE', 3600))

        return CoursVideoS3Storage()
    return FileSystemStorage(
        location=str(cours_video_local_root()),
        base_url=COURS_VIDEO_URL_PREFIX,
    )


def upload_to_cours_video(instance, filename):
    """Chemin multi-école : ecole/cours/fichier."""
    import os
    import uuid
    from django.utils.text import slugify

    base, ext = os.path.splitext(filename)
    ext = (ext or '.mp4').lower()
    safe = slugify(base)[:40] or 'video'
    unique = uuid.uuid4().hex[:10]

    ecole_id = '0'
    cours_id = '0'
    try:
        if getattr(instance, 'cours_id', None):
            cours = instance.cours
            cours_id = str(cours.pk)
            ecole_id = str(getattr(cours, 'ecole_id', None) or '0')
        elif getattr(instance, 'chapitre_id', None) and instance.chapitre_id:
            cours = instance.chapitre.cours
            cours_id = str(cours.pk)
            ecole_id = str(getattr(cours, 'ecole_id', None) or '0')
    except Exception:
        pass

    return f'{ecole_id}/{cours_id}/{safe}-{unique}{ext}'
