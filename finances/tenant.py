from common.tenant import get_user_ecole  # noqa: F401
from .models import TypeFrais, Frais_Scolaire, Paiement, TauxChange, BudgetAnnuel


def type_frais_for_ecole(ecole):
    if ecole is None:
        return TypeFrais.objects.none()
    return TypeFrais.objects.filter(ecole=ecole)


def frais_for_ecole(ecole):
    if ecole is None:
        return Frais_Scolaire.objects.none()
    # Année scolaire nationale partagée : cloisonnement via le type de frais (lié à l'école).
    return Frais_Scolaire.objects.filter(type_frais__ecole=ecole)


def paiements_for_ecole(ecole):
    if ecole is None:
        return Paiement.objects.none()
    return Paiement.objects.filter(eleve__eleve__ecole=ecole)


def taux_change_for_ecole(ecole):
    if ecole is None:
        return TauxChange.objects.none()
    return TauxChange.objects.filter(ecole=ecole)


def budgets_for_ecole(ecole):
    if ecole is None:
        return BudgetAnnuel.objects.none()
    return BudgetAnnuel.objects.filter(ecole=ecole)
