"""Helpers pour l'isolation des données GRH par école (multi-tenant)."""

from .models import Personnel, Contrat, Conge, Presence, Paie


def get_user_ecole(request):
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return None
    return getattr(request.user, "ecole", None)


def personnel_for_ecole(ecole):
    if ecole is None:
        return Personnel.objects.none()
    return Personnel.objects.filter(ecole=ecole)


def contrats_for_ecole(ecole):
    if ecole is None:
        return Contrat.objects.none()
    return Contrat.objects.filter(personnel__ecole=ecole)


def conges_for_ecole(ecole):
    if ecole is None:
        return Conge.objects.none()
    return Conge.objects.filter(personnel__ecole=ecole)


def presences_for_ecole(ecole):
    if ecole is None:
        return Presence.objects.none()
    return Presence.objects.filter(personnel__ecole=ecole)


def paies_for_ecole(ecole):
    if ecole is None:
        return Paie.objects.none()
    return Paie.objects.filter(personnel__ecole=ecole)
