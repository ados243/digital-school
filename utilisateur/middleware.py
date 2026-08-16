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
    '/mot-de-passe-oublie',
    '/reinitialiser-mot-de-passe',
    '/mon-espace',
    '/static',
    '/media',
    '/admin',
    '/sante',
)

# Les professeurs restent dans mon-espace (travaux, présences, classes).
PREFIXES_ENSEIGNANT = PREFIXES_AUTORISES

# Auth / profil / assets — communs aux rôles back-office restreints.
PREFIXES_COMMUNS = (
    '/connexion',
    '/deconnexion',
    '/bienvenue',
    '/mot-de-passe-oublie',
    '/reinitialiser-mot-de-passe',
    '/mon-espace/profil',
    '/static',
    '/media',
    '/sante',
)

# Le caissier n'accède qu'aux paiements élèves (et auth / static / profil).
PREFIXES_CAISSIER = PREFIXES_COMMUNS + (
    '/finances/paiements',
    '/finances/cloture',
)

# Trésorier / Comptable : module finances (trésorerie) complet.
PREFIXES_TRESORERIE = PREFIXES_COMMUNS + (
    '/finances',
)

# Directeur des études : pédagogie (+ classes liées au module).
PREFIXES_DIRECTEUR_ETUDES = PREFIXES_COMMUNS + (
    '/pedagogie',
)

# Secrétaire : inscriptions uniquement.
PREFIXES_SECRETAIRE = PREFIXES_COMMUNS + (
    '/inscription',
)

ROLES_RESTREINTS = ('PARENT', 'ELEVE')
ROLES_ENSEIGNANT = ('PROFESSEUR', 'ENSEIGNANT')


def _chemin_autorise(path, prefixes):
    path = path or ''
    return any(path.startswith(prefix) for prefix in prefixes)


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
    return _chemin_autorise(path, PREFIXES_CAISSIER)


def _chemin_autorise_directeur_etudes(path):
    path = path or ''
    if _chemin_autorise(path, PREFIXES_DIRECTEUR_ETUDES):
        return True
    # Classes & salles sont sous /inscription/classe mais appartiennent à la pédagogie.
    return path.startswith('/inscription/classe')


def _est_caissier(user):
    if getattr(user, 'is_superuser', False):
        return False
    return bool(getattr(user, 'is_caissier', False))


def _est_tresorerie(user):
    if getattr(user, 'is_superuser', False):
        return False
    return bool(getattr(user, 'is_tresorerie_restreinte', False))


def _est_directeur_etudes(user):
    if getattr(user, 'is_superuser', False):
        return False
    return bool(getattr(user, 'is_directeur_etudes', False))


def _est_secretaire(user):
    if getattr(user, 'is_superuser', False):
        return False
    return bool(getattr(user, 'is_secretaire', False))


def _est_prefet(user):
    if getattr(user, 'is_superuser', False):
        return False
    return bool(getattr(user, 'is_prefet', False))


def _est_promoteur(user):
    if getattr(user, 'is_superuser', False):
        return False
    return bool(getattr(user, 'is_promoteur', False))


def _chemin_action_ecriture(path):
    """URLs de création / modification / suppression (hors simple consultation)."""
    path = (path or '').rstrip('/')
    marqueurs = (
        '/create',
        '/nouveau',
        '/nouvelle',
        '/modifier',
        '/supprimer',
        '/update',
        '/delete',
        '/demande',
        '/approuver',
        '/rejeter',
        '/pointer',
        '/generer',
        '/payer',
        '/inscrire',
        '/publier',
        '/renvoyer',
        '/seed',
        '/generer-demo',
    )
    if any(m in path for m in marqueurs):
        return True
    return path.endswith(('/create', '/nouveau', '/nouvelle', '/modifier', '/supprimer'))


def _chemin_autorise_prefet(request):
    """Préfet : voit tout sauf finances ; n'écrit que dans le GRH (+ profil)."""
    path = request.path or ''
    method = (request.method or 'GET').upper()

    if _chemin_autorise(path, PREFIXES_COMMUNS):
        return True

    # Pas d'admin Django ni de finances.
    if path.startswith('/admin') or path.startswith('/finances'):
        return False

    # GRH : lecture et écriture.
    if path.startswith('/grh'):
        return True

    # Hors GRH : consultation uniquement (GET/HEAD/OPTIONS).
    if method in ('GET', 'HEAD', 'OPTIONS') and not _chemin_action_ecriture(path):
        return True

    return False


def _chemin_autorise_promoteur(request):
    """Promoteur : voit tout ; ne modifie rien (sauf profil)."""
    path = request.path or ''
    method = (request.method or 'GET').upper()

    if _chemin_autorise(path, PREFIXES_COMMUNS):
        return True

    if path.startswith('/admin'):
        return False

    if method in ('GET', 'HEAD', 'OPTIONS') and not _chemin_action_ecriture(path):
        return True

    return False


def _rediriger_restreint(request, path, cible_name, message):
    """Redirige vers la cible du module autorisé, sans boucle 302."""
    cible = reverse(cible_name)
    if path.rstrip('/') == cible.rstrip('/'):
        return None
    messages.warning(request, message)
    return redirect(cible)


class RestrictionPortailMiddleware:
    """Cantonne les comptes aux espaces correspondant à leur rôle / fonction.

    - Parent / Élève : uniquement mon-espace
    - Caissier (rôle ou fonction GRH) : uniquement paiements élèves (prioritaire)
    - Trésorier / Comptable : uniquement finances (trésorerie)
    - Directeur des études : uniquement pédagogie
    - Secrétaire : uniquement inscriptions
    - Préfet : tout sauf finances ; modifications uniquement en GRH
    - Promoteur : tout en lecture seule
    - Professeur / Enseignant : uniquement mon-espace
    - Autres (Manager / Directeur…) : accès général ; finances en consultation,
      sans pouvoir passer / modifier les écritures (réservé trésorerie)
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

            # Caissier avant les autres rôles finance / staff.
            if _est_caissier(user):
                if _chemin_autorise_caissier(path):
                    return self.get_response(request)
                redir = _rediriger_restreint(
                    request,
                    path,
                    'finances:paiement_list',
                    "Accès réservé : en tant que caissier, vous ne pouvez effectuer que les paiements.",
                )
                return redir or self.get_response(request)

            if _est_tresorerie(user):
                if _chemin_autorise(path, PREFIXES_TRESORERIE):
                    return self.get_response(request)
                redir = _rediriger_restreint(
                    request,
                    path,
                    'finances:dashboard',
                    "Accès réservé : en tant que trésorier / comptable, vous n'avez accès qu'à la trésorerie.",
                )
                return redir or self.get_response(request)

            if _est_directeur_etudes(user):
                if _chemin_autorise_directeur_etudes(path):
                    return self.get_response(request)
                redir = _rediriger_restreint(
                    request,
                    path,
                    'pedagogie:dashboard',
                    "Accès réservé : en tant que directeur des études, vous n'avez accès qu'à la pédagogie.",
                )
                return redir or self.get_response(request)

            if _est_secretaire(user):
                if _chemin_autorise(path, PREFIXES_SECRETAIRE):
                    return self.get_response(request)
                redir = _rediriger_restreint(
                    request,
                    path,
                    'inscription:dashboard',
                    "Accès réservé : en tant que secrétaire, vous n'avez accès qu'aux inscriptions.",
                )
                return redir or self.get_response(request)

            if _est_prefet(user):
                if _chemin_autorise_prefet(request):
                    return self.get_response(request)
                if path.startswith('/finances'):
                    msg = "Accès réservé : en tant que préfet, vous n'avez pas accès aux finances."
                else:
                    msg = "Accès réservé : en tant que préfet, vous ne pouvez modifier que le module GRH."
                redir = _rediriger_restreint(request, path, 'grh:dashboard', msg)
                return redir or self.get_response(request)

            if _est_promoteur(user):
                if _chemin_autorise_promoteur(request):
                    return self.get_response(request)
                redir = _rediriger_restreint(
                    request,
                    path,
                    'grh:dashboard',
                    "Accès réservé : en tant que promoteur, vous pouvez consulter mais pas modifier.",
                )
                return redir or self.get_response(request)

            if role in ROLES_ENSEIGNANT and not path.startswith(PREFIXES_ENSEIGNANT):
                return redirect('utilisateur:enseignant_dashboard')

            # Écritures : seuls trésorier / comptable (et superuser) peuvent passer / modifier.
            if (
                path.startswith('/finances/hoada/ecritures/create')
                and not getattr(user, 'is_superuser', False)
                and not getattr(user, 'peut_gerer_ecritures', False)
            ):
                redir = _rediriger_restreint(
                    request,
                    path,
                    'finances:hoada_ecritures_list',
                    "Accès réservé : seuls le trésorier et le comptable peuvent passer ou modifier les écritures.",
                )
                return redir or self.get_response(request)

            # Finances : trésorerie, manager, directeur, promoteur (consultation) ; autres bloqués.
            if path.startswith('/finances') and not getattr(user, 'is_superuser', False):
                if not getattr(user, 'peut_acceder_finances', False):
                    redir = _rediriger_restreint(
                        request,
                        path,
                        'grh:dashboard',
                        "Accès réservé : vous n'avez pas accès au module finances.",
                    )
                    return redir or self.get_response(request)

        return self.get_response(request)
