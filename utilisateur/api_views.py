"""API lecture session (parent / enseignant / élève)."""

from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from utilisateur.views import _enfants_parent_enrichis, _inscription_courante, _finances_inscription


def _dec(value):
    if value is None:
        return "0"
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value)


@login_required
def api_moi(request):
    user = request.user
    payload = {
        "id": user.pk,
        "username": user.username,
        "prenom": user.prenom,
        "role": user.role,
        "ecole": getattr(user.ecole, "ecole", None),
        "ecole_id": user.ecole_id,
    }
    if user.is_parent and user.tuteur_id:
        enfants = []
        for item in _enfants_parent_enrichis(user):
            el = item["eleve"]
            ins = item["inscription"]
            fin = item["finances"]
            enfants.append({
                "id": el.pk,
                "nom": f"{el.prenom} {el.nom}",
                "matricule": el.matricule,
                "classe": ins.classe.classe if ins else None,
                "impayes": fin["nb_impayes"],
                "reste": _dec(fin["total_du"]),
                "presence": item["presence"]["taux"],
            })
        payload["enfants"] = enfants
    elif user.is_eleve and user.eleve_id:
        ins = _inscription_courante(user.eleve)
        fin = _finances_inscription(ins)
        payload["eleve"] = {
            "id": user.eleve_id,
            "classe": ins.classe.classe if ins else None,
            "impayes": fin["nb_impayes"],
            "reste": _dec(fin["total_du"]),
        }
    return JsonResponse(payload)
