from .models import TypeFrais, Frais_Scolaire, Paiement, TauxChange


def get_user_ecole(request):
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return None
    return getattr(request.user, "ecole", None)


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
