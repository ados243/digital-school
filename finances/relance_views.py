"""Vue Finances : relances WhatsApp des soldes impayés."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from finances.models import ConfigWhatsApp
from finances.relances import lister_dettes, relancer_dettes
from finances.tenant import get_user_ecole


@login_required
def relances_impayes(request):
    """Liste des élèves en dette + envoi WhatsApp du solde aux tuteurs."""
    ecole = get_user_ecole(request)
    lignes, annee = lister_dettes(ecole)
    config = ConfigWhatsApp.charger_pour_ecole(ecole) if ecole else None
    whatsapp_ok = bool(config and config.actif)
    nb_envoyables = sum(1 for l in lignes if l["peut_envoyer"])
    return render(request, "finances/relances_impayes.html", {
        "lignes": lignes,
        "annee": annee,
        "ecole": ecole,
        "whatsapp_ok": whatsapp_ok,
        "nb_dettes": len(lignes),
        "nb_envoyables": nb_envoyables,
        "nb_sans_tel": len(lignes) - nb_envoyables,
        "exemple_message": lignes[0]["message"] if lignes else "",
    })


@login_required
@require_POST
def relances_impayes_envoyer(request):
    ecole = get_user_ecole(request)
    if not ecole:
        messages.error(request, "Aucune école associée à votre compte.")
        return redirect("finances:relances_impayes")

    inscription_id = (request.POST.get("inscription_id") or "").strip() or None
    stats = relancer_dettes(ecole, inscription_id=inscription_id)

    if stats["erreurs"] and not stats["envoyes"] and not stats["echecs"]:
        messages.error(request, stats["erreurs"][0])
        return redirect("finances:relances_impayes")

    if stats["envoyes"]:
        cible = "ce parent" if inscription_id else f"{stats['envoyes']} parent(s)"
        messages.success(
            request,
            f"Relance minerval envoyée à {cible} avec le détail du reste dû.",
        )
    if stats["echecs"]:
        apercu = " ; ".join(stats["erreurs"][:3])
        messages.error(
            request,
            f"{stats['echecs']} envoi(s) ont échoué. {apercu}",
        )
    if stats["ignores"] and not inscription_id:
        messages.warning(
            request,
            f"{stats['ignores']} fiche(s) ignorée(s) (numéro WhatsApp manquant).",
        )
    if not stats["envoyes"] and not stats["echecs"] and not stats["erreurs"]:
        messages.info(request, "Aucun parent à relancer pour le moment.")
    return redirect("finances:relances_impayes")
