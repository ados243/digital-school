"""Lecture authentifiée et autorisée des fichiers médias (photos, avatars, cours)."""

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.views.static import serve


def _norm(path):
    return (path or "").replace("\\", "/").lstrip("/")


def _noms_egaux(fichier, relative):
    nom = getattr(fichier, "name", None) or ""
    return bool(nom) and _norm(nom) == relative


def _ecole_ids_utilisateur(user):
    ids = set()
    for attr in ("ecole_id",):
        val = getattr(user, attr, None)
        if val:
            ids.add(val)
    tuteur = getattr(user, "tuteur", None)
    if tuteur is not None and getattr(tuteur, "ecole_id", None):
        ids.add(tuteur.ecole_id)
    eleve = getattr(user, "eleve", None)
    if eleve is not None and getattr(eleve, "ecole_id", None):
        ids.add(eleve.ecole_id)
    return ids


def peut_lire_media(user, relative):
    """True si l'utilisateur peut voir ce fichier relatif à MEDIA_ROOT."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    relative = _norm(relative)
    if not relative:
        return False

    if getattr(user, "avatar", None) and _noms_egaux(user.avatar, relative):
        return True

    from inscription.models import Eleve
    from grh.models import Personnel

    eleve = Eleve.objects.filter(photo=relative).select_related("ecole", "titeur").first()
    if eleve is not None:
        if getattr(user, "eleve_id", None) == eleve.pk:
            return True
        if getattr(user, "tuteur_id", None) and eleve.titeur_id == user.tuteur_id:
            return True
        if eleve.ecole_id in _ecole_ids_utilisateur(user) and not getattr(user, "is_parent", False) and not getattr(user, "is_eleve", False):
            return True
        return False

    personnel = Personnel.objects.filter(photo=relative).select_related("ecole").first()
    if personnel is not None:
        if getattr(personnel, "utilisateur_id", None) == user.pk:
            return True
        if personnel.ecole_id in _ecole_ids_utilisateur(user) and not getattr(user, "is_parent", False) and not getattr(user, "is_eleve", False):
            return True
        return False

    from utilisateur.models import Utilisateur

    titulaire = Utilisateur.objects.filter(avatar=relative).select_related("ecole").first()
    if titulaire is not None:
        if titulaire.pk == user.pk:
            return True
        if titulaire.ecole_id in _ecole_ids_utilisateur(user) and not getattr(user, "is_parent", False) and not getattr(user, "is_eleve", False):
            return True
        return False

    from pedagogie.models import ChapitreCours, CoursEnLigne, LeconEnLigne

    cours = CoursEnLigne.objects.filter(image_couverture=relative).first()
    if cours is not None:
        return cours.ecole_id in _ecole_ids_utilisateur(user)

    chapitre = (
        ChapitreCours.objects.filter(image=relative)
        .select_related("cours")
        .first()
    )
    if chapitre is not None:
        return getattr(chapitre.cours, "ecole_id", None) in _ecole_ids_utilisateur(user)

    lecon = (
        LeconEnLigne.objects.filter(image=relative)
        .select_related("chapitre__cours", "cours")
        .first()
    )
    if lecon is None:
        lecon = (
            LeconEnLigne.objects.filter(fichier=relative)
            .select_related("chapitre__cours", "cours")
            .first()
        )
    if lecon is not None:
        cours = getattr(lecon, "cours", None) or getattr(
            getattr(lecon, "chapitre", None), "cours", None
        )
        return getattr(cours, "ecole_id", None) in _ecole_ids_utilisateur(user)

    from pedagogie.models import RessourcePartagee

    ressource = RessourcePartagee.objects.filter(fichier=relative).select_related(
        "ecole", "enseignant"
    ).prefetch_related("classes").first()
    if ressource is not None:
        if getattr(user, "is_superuser", False):
            return True
        if ressource.ecole_id not in _ecole_ids_utilisateur(user):
            return False
        if getattr(user, "is_eleve", False):
            from utilisateur.views import _inscription_courante
            eleve = getattr(user, "eleve", None)
            inscription = _inscription_courante(eleve) if eleve else None
            return bool(
                ressource.publie
                and inscription
                and ressource.concerne_classe(inscription.classe)
            )
        if getattr(user, "is_parent", False):
            return False
        return True

    return False


@login_required
def servir_media(request, path):
    """Photos d'élèves, avatars et supports de cours : auth + appartenance à l'école."""
    relative = _norm(path)
    if not relative or ".." in relative.split("/"):
        raise Http404()
    if not peut_lire_media(request.user, relative):
        raise Http404()
    return serve(request, relative, document_root=str(settings.MEDIA_ROOT))
