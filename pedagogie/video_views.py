"""Lecture authentifiée des vidéos de cours (stockage local privé)."""
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.views.static import serve

from .storage import cloud_media_configured, cours_video_local_root


def _ecoles_utilisateur(user):
    ids = set()
    ecole_id = getattr(user, 'ecole_id', None)
    if ecole_id:
        ids.add(str(ecole_id))
    tuteur = getattr(user, 'tuteur', None)
    if tuteur is not None:
        tid = getattr(tuteur, 'ecole_id', None)
        if tid:
            ids.add(str(tid))
    eleve = getattr(user, 'eleve', None)
    if eleve is not None:
        eid = getattr(eleve, 'ecole_id', None)
        if eid:
            ids.add(str(eid))
    return ids


@login_required
def servir_video_cours(request, relative_path):
    """Sert un fichier vidéo local après contrôle d'appartenance à l'école."""
    if cloud_media_configured():
        raise Http404()

    relative_path = (relative_path or '').replace('\\', '/').lstrip('/')
    if not relative_path or '..' in relative_path.split('/'):
        raise Http404()

    ecole_id = relative_path.split('/', 1)[0]
    user = request.user
    if not user.is_superuser and ecole_id not in _ecoles_utilisateur(user):
        raise Http404()

    return serve(
        request,
        relative_path,
        document_root=str(cours_video_local_root()),
    )
