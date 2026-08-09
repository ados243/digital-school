"""Contexte partagé du portail (parent / élève / enseignant)."""


def portail_enseignant(request):
    """Expose si le prof connecté est titulaire d'au moins une classe."""
    user = getattr(request, 'user', None)
    if not user or not getattr(user, 'is_authenticated', False):
        return {'est_titulaire_quelconque': False}
    if not getattr(user, 'is_professeur', False):
        return {'est_titulaire_quelconque': False}
    try:
        from grh.models import Personnel
        from inscription.models import Classe

        personnel = Personnel.objects.filter(utilisateur=user).only('id').first()
        if not personnel:
            return {'est_titulaire_quelconque': False}
        return {
            'est_titulaire_quelconque': Classe.objects.filter(titulaire=personnel).exists()
        }
    except Exception:
        return {'est_titulaire_quelconque': False}
