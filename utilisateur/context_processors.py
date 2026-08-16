"""Contexte partagé du portail (parent / élève / enseignant)."""


def portail_enseignant(request):
    """Expose le statut titulaire et le nom de l'école de l'utilisateur connecté."""
    ctx = {
        'est_titulaire_quelconque': False,
        'nom_ecole': '',
    }
    user = getattr(request, 'user', None)
    if not user or not getattr(user, 'is_authenticated', False):
        return ctx

    ecole = getattr(user, 'ecole', None)
    if ecole is not None:
        ctx['nom_ecole'] = getattr(ecole, 'ecole', '') or ''

    if not getattr(user, 'is_professeur', False):
        return ctx
    try:
        from grh.models import Personnel
        from inscription.models import Classe

        personnel = Personnel.objects.filter(utilisateur=user).only('id').first()
        if not personnel:
            return ctx
        ctx['est_titulaire_quelconque'] = Classe.objects.filter(titulaire=personnel).exists()
    except Exception:
        pass
    return ctx
