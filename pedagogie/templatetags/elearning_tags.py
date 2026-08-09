from django import template
import re

register = template.Library()


@register.filter
def video_embed(url):
    """Retourne une URL d'embed YouTube/Vimeo ou None."""
    if not url:
        return ''
    url = url.strip()
    # YouTube
    m = re.search(
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([A-Za-z0-9_-]{6,})',
        url,
    )
    if m:
        return f'https://www.youtube.com/embed/{m.group(1)}'
    # Vimeo
    m = re.search(r'vimeo\.com/(?:video/)?(\d+)', url)
    if m:
        return f'https://player.vimeo.com/video/{m.group(1)}'
    return ''


@register.filter
def type_lecon_icon(type_contenu):
    return {
        'VIDEO': '▶',
        'LECTURE': '📖',
        'DOCUMENT': '📎',
        'EXERCICE': '✏️',
    }.get(type_contenu, '•')
