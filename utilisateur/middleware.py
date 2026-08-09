from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse

# Préfixes toujours accessibles, y compris pour les profils Parent / Élève :
# authentification, espace personnel, fichiers statiques/médias et admin Django.
PREFIXES_AUTORISES = (
    '/connexion',
    '/deconnexion',
    '/creer-compte',
    '/bienvenue',
    '/mon-espace',
    '/static',
    '/media',
    '/admin',
)

# Les professeurs restent dans mon-espace (travaux, présences, classes).
PREFIXES_ENSEIGNANT = PREFIXES_AUTORISES

# Le caissier n'accède qu'aux paiements élèves (et auth / static).
PREFIXES_CAISSIER = (
    '/connexion',
    '/deconnexion',
    '/bienvenue',
    '/static',
    '/media',
    '/finances/paiements',
)

ROLES_RESTREINTS = ('PARENT', 'ELEVE')
ROLES_ENSEIGNANT = ('PROFESSEUR', 'ENSEIGNANT')


def _chemin_autorise_caissier(path):
    path = path or ''
    if path.rstrip('/') == '/finances':
        return False
    # Modification / suppression interdites aux caissiers (création / impression OK).
    if (
        '/modifier/' in path
        or path.rstrip('/').endswith('/modifier')
        or '/supprimer/' in path
        or path.rstrip('/').endswith('/supprimer')
    ):
        return False
    return any(path.startswith(prefix) for prefix in PREFIXES_CAISSIER)


def _est_caissier(user):
    if getattr(user, 'is_superuser', False):
        return False
    return bool(getattr(user, 'is_caissier', False))


class RestrictionPortailMiddleware:
    """Cantonne les comptes Parent, Élève, Enseignant et Caissier à leurs espaces.

    - Parent / Élève : uniquement mon-espace
    - Caissier (rôle ou fonction GRH) : uniquement paiements élèves (prioritaire)
    - Professeur / Enseignant : uniquement mon-espace
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user is not None and getattr(user, 'is_authenticated', False):
            role = getattr(user, 'role', None)
            path = request.path or ''

            if role in ROLES_RESTREINTS and not path.startswith(PREFIXES_AUTORISES):
                return redirect('utilisateur:portail')

            # Caissier avant enseignant : un personnel « Caissier » ne doit jamais
            # être renvoyé vers l'espace professeur depuis /finances/paiements/.
            if _est_caissier(user):
                if _chemin_autorise_caissier(path):
                    return self.get_response(request)
                # Évite une boucle 302 si l'on est déjà sur la cible.
                cible = reverse('finances:paiement_list')
                if path.rstrip('/') == cible.rstrip('/'):
                    return self.get_response(request)
                messages.warning(
                    request,
                    "Accès réservé : en tant que caissier, vous ne pouvez effectuer que les paiements.",
                )
                return redirect(cible)

            if role in ROLES_ENSEIGNANT and not path.startswith(PREFIXES_ENSEIGNANT):
                return redirect('utilisateur:enseignant_dashboard')

        return self.get_response(request)
