"""Helpers pour l'isolation des données GRH par école (multi-tenant)."""

from common.tenant import get_user_ecole  # noqa: F401
from .models import Personnel, Contrat, Conge, Presence, Paie


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
