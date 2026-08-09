"""Helpers pour l'isolation des données par école (multi-tenant)."""

from .models import Eleve, Tuteur, Inscription, Classe, Annee_Scolaire, Section


def get_user_ecole(request):
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return None
    return getattr(request.user, "ecole", None)


def eleves_for_ecole(ecole):
    if ecole is None:
        return Eleve.objects.none()
    return Eleve.objects.filter(ecole=ecole)


def tuteurs_for_ecole(ecole):
    if ecole is None:
        return Tuteur.objects.none()
    return Tuteur.objects.filter(ecole=ecole)


def inscriptions_for_ecole(ecole):
    if ecole is None:
        return Inscription.objects.none()
    return Inscription.objects.filter(classe__ecole=ecole)


def classes_for_ecole(ecole):
    if ecole is None:
        return Classe.objects.none()
    return Classe.objects.filter(ecole=ecole)


def sections_for_ecole(ecole):
    """Sections effectivement utilisées par les classes de l'école."""
    if ecole is None:
        return Section.objects.none()
    return Section.objects.filter(classe__ecole=ecole).distinct()


def annees_for_ecole(ecole):
    """Années scolaires nationales (identiques pour toutes les écoles).

    Le paramètre ``ecole`` sert uniquement de garde multi-tenant :
    sans école connectée, aucun résultat n'est renvoyé.
    """
    if ecole is None:
        return Annee_Scolaire.objects.none()
    return Annee_Scolaire.objects.all()


def annee_en_cours():
    """Année scolaire nationale marquée en cours (calendrier MINEDU-NC)."""
    return Annee_Scolaire.objects.filter(est_encoure=True).first()
