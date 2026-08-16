from django import template

register = template.Library()


@register.filter
def video_playback_url(fichier):
    """URL de lecture (signée si stockage cloud, sinon MEDIA local)."""
    if not fichier:
        return ''
    try:
        return fichier.url
    except Exception:
        return ''


@register.filter
def type_lecon_icon(type_contenu):
    return {
        'VIDEO': '▶',
        'LECTURE': '📖',
        'DOCUMENT': '📎',
        'EXERCICE': '✏️',
    }.get(type_contenu, '•')
