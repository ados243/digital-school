"""Isolation multi-école : un seul get_user_ecole pour toute l'application."""


def get_user_ecole(request):
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return None
    return getattr(request.user, "ecole", None)
