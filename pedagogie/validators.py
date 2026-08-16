"""Validateurs pour les médias pédagogiques."""
from django.core.exceptions import ValidationError
from django.conf import settings


VIDEO_EXTENSIONS = {'.mp4', '.webm', '.ogg', '.mov', '.m4v'}
VIDEO_CONTENT_TYPES = {
    'video/mp4',
    'video/webm',
    'video/ogg',
    'video/quicktime',
    'video/x-m4v',
}


def cours_video_max_mb():
    """Taille maximale autorisée par vidéo (Mo), configurable via COURS_VIDEO_MAX_MB."""
    try:
        return max(1, int(getattr(settings, 'COURS_VIDEO_MAX_MB', 70)))
    except (TypeError, ValueError):
        return 70


def cours_video_max_bytes():
    return cours_video_max_mb() * 1024 * 1024


def validate_cours_video(fichier):
    """Contrôle extension, type MIME et taille max des vidéos de cours."""
    if not fichier:
        return

    nom = getattr(fichier, 'name', '') or ''
    lower = nom.lower()
    if not any(lower.endswith(ext) for ext in VIDEO_EXTENSIONS):
        raise ValidationError(
            'Format non supporté. Utilisez une vidéo MP4 ou WebM (recommandé : MP4 H.264).'
        )

    content_type = getattr(fichier, 'content_type', '') or ''
    if content_type and content_type not in VIDEO_CONTENT_TYPES and not content_type.startswith('video/'):
        raise ValidationError('Le fichier envoyé n’est pas une vidéo valide.')

    max_mb = cours_video_max_mb()
    max_bytes = cours_video_max_bytes()
    taille = getattr(fichier, 'size', None)
    if taille is None:
        # Fichier déjà stocké sans taille accessible : on ne bloque pas
        return
    if taille > max_bytes:
        raise ValidationError(
            f'La vidéo dépasse la taille maximale autorisée ({max_mb} Mo). '
            f'Taille du fichier : {taille / (1024 * 1024):.1f} Mo.'
        )
