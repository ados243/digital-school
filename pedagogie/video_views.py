"""Lecture authentifiée des vidéos de cours (stockage local privé)."""
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404
from django.views.static import serve

from .models import ChapitreCours, CoursEnLigne, LeconEnLigne, RessourcePartagee, qs_pour_classe
from .storage import cloud_media_configured, cours_video_local_root


def _norm(path):
    return (path or "").replace("\\", "/").lstrip("/")


def _ecoles_utilisateur(user):
    ids = set()
    ecole_id = getattr(user, "ecole_id", None)
    if ecole_id:
        ids.add(str(ecole_id))
    tuteur = getattr(user, "tuteur", None)
    if tuteur is not None:
        tid = getattr(tuteur, "ecole_id", None)
        if tid:
            ids.add(str(tid))
    eleve = getattr(user, "eleve", None)
    if eleve is not None:
        eid = getattr(eleve, "ecole_id", None)
        if eid:
            ids.add(str(eid))
    return ids


def _inscription_eleve(user):
    from utilisateur.views import _inscription_courante

    eleve = getattr(user, "eleve", None)
    if eleve is None:
        return None, None
    return eleve, _inscription_courante(eleve)


def _peut_lire_cours(user, cours):
    if cours is None:
        return False
    if getattr(user, "is_superuser", False):
        return True
    if str(cours.ecole_id) not in _ecoles_utilisateur(user):
        return False

    # Staff école (hors parent/élève) : lecture des contenus de l'école
    if (
        not getattr(user, "is_parent", False)
        and not getattr(user, "is_eleve", False)
        and getattr(user, "ecole_id", None) == cours.ecole_id
    ):
        return True

    personnel = getattr(user, "personnel", None)
    if personnel is not None and personnel.ecole_id == cours.ecole_id:
        if cours.enseignant_id == personnel.id:
            return True
        from pedagogie.affectations import peut_gerer_matiere_classes

        return peut_gerer_matiere_classes(
            personnel, cours.matiere, cours.classes_concernees()
        )

    if getattr(user, "is_eleve", False):
        eleve, inscription = _inscription_eleve(user)
        if not inscription or not cours.publie:
            return False
        if cours.ecole_id != eleve.ecole_id:
            return False
        return qs_pour_classe(
            CoursEnLigne.objects.filter(pk=cours.pk),
            inscription.classe,
        ).exists()

    if getattr(user, "is_parent", False):
        tuteur = getattr(user, "tuteur", None)
        if tuteur is None:
            return False
        from inscription.models import Eleve
        from utilisateur.views import _inscription_courante

        for eleve in Eleve.objects.filter(titeur=tuteur, ecole_id=cours.ecole_id):
            inscription = _inscription_courante(eleve)
            if not inscription or not cours.publie:
                continue
            if qs_pour_classe(
                CoursEnLigne.objects.filter(pk=cours.pk),
                inscription.classe,
            ).exists():
                return True
        return False

    return False


def _peut_lire_ressource(user, ressource):
    if ressource is None:
        return False
    if getattr(user, "is_superuser", False):
        return True
    if str(ressource.ecole_id) not in _ecoles_utilisateur(user):
        return False
    if (
        not getattr(user, "is_parent", False)
        and not getattr(user, "is_eleve", False)
        and getattr(user, "ecole_id", None) == ressource.ecole_id
    ):
        return True
    personnel = getattr(user, "personnel", None)
    if personnel is not None and (
        ressource.enseignant_id == personnel.id
        or ressource.ecole_id == personnel.ecole_id
    ):
        return True
    if getattr(user, "is_eleve", False):
        eleve, inscription = _inscription_eleve(user)
        if not inscription:
            return False
        classes = list(ressource.classes.all())
        if not classes:
            return True
        return any(c.pk == inscription.classe_id for c in classes)
    if getattr(user, "is_parent", False):
        tuteur = getattr(user, "tuteur", None)
        if tuteur is None:
            return False
        from inscription.models import Eleve
        from utilisateur.views import _inscription_courante

        classes_ids = {c.pk for c in ressource.classes.all()}
        for eleve in Eleve.objects.filter(titeur=tuteur, ecole_id=ressource.ecole_id):
            inscription = _inscription_courante(eleve)
            if inscription and (not classes_ids or inscription.classe_id in classes_ids):
                return True
        return False
    return False


def _autoriser_video(user, relative_path):
    """True si le fichier vidéo appartient à un contenu accessible à l'utilisateur."""
    relative = _norm(relative_path)
    if not relative:
        return False

    lecon = (
        LeconEnLigne.objects.filter(video=relative)
        .select_related("cours", "chapitre__cours", "cours__matiere")
        .first()
    )
    if lecon is not None:
        cours = lecon.cours or getattr(lecon.chapitre, "cours", None)
        if not _peut_lire_cours(user, cours):
            return False
        if getattr(user, "is_eleve", False) or getattr(user, "is_parent", False):
            if not lecon.publie:
                return False
            chap = lecon.chapitre
            if chap is not None and not chap.publie:
                return False
        return True

    chapitre = (
        ChapitreCours.objects.filter(video=relative)
        .select_related("cours", "cours__matiere")
        .first()
    )
    if chapitre is not None:
        if not _peut_lire_cours(user, chapitre.cours):
            return False
        if (getattr(user, "is_eleve", False) or getattr(user, "is_parent", False)) and not chapitre.publie:
            return False
        return True

    ressource = (
        RessourcePartagee.objects.filter(Q(video=relative) | Q(fichier=relative))
        .select_related("ecole", "enseignant")
        .prefetch_related("classes")
        .first()
    )
    if ressource is not None:
        return _peut_lire_ressource(user, ressource)

    # Fichier orphelin : refuser (sauf superuser déjà géré en amont)
    return False


@login_required
def servir_video_cours(request, relative_path):
    """Sert un fichier vidéo local après contrôle d'accès au cours / ressource."""
    if cloud_media_configured():
        raise Http404()

    relative_path = _norm(relative_path)
    if not relative_path or ".." in relative_path.split("/"):
        raise Http404()

    user = request.user
    if not user.is_superuser:
        ecole_id = relative_path.split("/", 1)[0]
        if ecole_id not in _ecoles_utilisateur(user):
            raise Http404()
        if not _autoriser_video(user, relative_path):
            raise Http404()

    return serve(
        request,
        relative_path,
        document_root=str(cours_video_local_root()),
    )
