"""Intentions de paiement Mobile Money (parent + webhook opérateur)."""

import hmac

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from common.tenant import get_user_ecole
from finances.models import IntentionPaiementMobile, Paiement
from finances.paiement_utils import frais_disponibles_pour_inscription
from finances.tenant import paiements_for_ecole
from inscription.models import Eleve
from utilisateur.views import _inscription_courante


def _attribuer_numero_recu(ecole, paiement):
    if paiement.numero_recu:
        return
    year_month = timezone.now().strftime("%Y%m")
    last_paiement = (
        paiements_for_ecole(ecole)
        .filter(numero_recu__startswith=f"REC-{year_month}")
        .order_by("id")
        .last()
    )
    last_seq = 0
    if last_paiement and last_paiement.numero_recu:
        try:
            last_seq = int(last_paiement.numero_recu.split("-")[-1])
        except ValueError:
            last_seq = 0
    paiement.numero_recu = f"REC-{year_month}-{last_seq + 1:04d}"


def _intentions_actives(inscription):
    return IntentionPaiementMobile.objects.filter(
        inscription=inscription,
        statut__in=("INITIEE", "EN_ATTENTE"),
    ).select_related("frais", "devise")


@login_required
def parent_payer_mobile(request, pk):
    """Le parent initie un paiement Mobile Money pour un enfant."""
    user = request.user
    if not user.is_parent or not user.tuteur_id:
        return redirect("utilisateur:portail")
    eleve = get_object_or_404(Eleve, pk=pk, titeur=user.tuteur)
    inscription = _inscription_courante(eleve)
    if not inscription:
        messages.error(request, "Aucune inscription en cours pour cet enfant.")
        return redirect("utilisateur:parent_enfant", pk=eleve.pk)

    ecole = eleve.ecole
    dus = frais_disponibles_pour_inscription(ecole, inscription)
    if request.method == "POST":
        frais_id = request.POST.get("frais_id")
        provider = request.POST.get("provider") or "AIRTEL"
        tel = (request.POST.get("telephone") or "").strip() or (user.tuteur.telephone or "")
        choix = next((d for d in dus if str(d["frais"].id) == str(frais_id)), None)
        if not choix or not tel:
            messages.error(request, "Choisissez un frais et un numéro Mobile Money.")
        else:
            frais = choix["frais"]
            intention = IntentionPaiementMobile.objects.create(
                ecole=ecole,
                inscription=inscription,
                frais=frais,
                montant=choix["reste"],
                devise=frais.devise,
                telephone=tel,
                provider=provider,
                statut="EN_ATTENTE",
            )
            messages.success(
                request,
                f"Demande {intention.reference} enregistrée. Composez le USSD de {intention.get_provider_display()} "
                f"puis communiquez la référence à la caisse, ou attendez la confirmation opérateur.",
            )
            return redirect("utilisateur:parent_enfant", pk=eleve.pk)

    return render(request, "utilisateur/parent_paiement_mobile.html", {
        "eleve": eleve,
        "inscription": inscription,
        "dus": dus,
        "providers": IntentionPaiementMobile.PROVIDER_CHOICES,
        "telephone": (user.tuteur.telephone or ""),
        "ussd": getattr(settings, "MOBILE_MONEY_USSD", {}) or {
            "AIRTEL": "*501#",
            "ORANGE": "*144#",
            "MPESA": "*150#",
        },
    })


@login_required
def caisse_confirmer_mobile(request, pk):
    """La caisse marque une intention comme payée et crée le reçu."""
    ecole = get_user_ecole(request)
    if not (
        request.user.is_superuser
        or getattr(request.user, "is_caissier", False)
        or getattr(request.user, "peut_acceder_finances", False)
    ):
        return HttpResponseForbidden("non autorisé")
    intention = get_object_or_404(IntentionPaiementMobile, pk=pk, ecole=ecole)
    if request.method != "POST":
        return redirect("finances:paiement_list")
    if intention.statut == "PAYEE":
        messages.info(request, "Cette intention est déjà payée.")
        return redirect("finances:paiement_list")
    if not intention.frais_id:
        messages.error(request, "Frais manquant sur l'intention.")
        return redirect("finances:paiement_list")

    paiement = Paiement(
        eleve=intention.inscription,
        frais=intention.frais,
        montant_paye=intention.montant,
        devise=intention.devise,
        mode_paiement="MOBILE_MONEY",
        reference_trans=intention.reference[:25],
        caissier=(request.user.get_username() or "")[:30],
        statut="VALIDE",
    )
    _attribuer_numero_recu(ecole, paiement)
    paiement.save()
    intention.statut = "PAYEE"
    intention.paiement = paiement
    intention.save(update_fields=["statut", "paiement", "updated_at"])
    messages.success(request, f"Paiement {paiement.numero_recu} enregistré ({intention.reference}).")
    return redirect("finances:paiement_print", pk=paiement.pk)


@csrf_exempt
@require_POST
def mobile_money_webhook(request):
    """Callback opérateur : authentification par en-tête X-Webhook-Token uniquement."""
    attendu = (getattr(settings, "MOBILE_MONEY_WEBHOOK_TOKEN", "") or "").strip()
    recu = (request.headers.get("X-Webhook-Token") or "").strip()
    if not attendu or not hmac.compare_digest(recu, attendu):
        return HttpResponseForbidden("token invalide")

    ref = (request.POST.get("reference") or "").strip()
    statut = (request.POST.get("statut") or "PAYEE").upper()
    operateur = (request.POST.get("transaction_id") or "")[:80]
    if not ref:
        return JsonResponse({"ok": False, "error": "reference manquante"}, status=400)

    with transaction.atomic():
        intention = (
            IntentionPaiementMobile.objects.select_for_update()
            .filter(reference=ref)
            .first()
        )
        if not intention:
            return JsonResponse({"ok": False, "error": "reference inconnue"}, status=404)

        if (
            statut in ("PAYEE", "SUCCESS", "SUCCESSFUL")
            and intention.statut != "PAYEE"
            and intention.frais_id
        ):
            paiement = Paiement(
                eleve=intention.inscription,
                frais=intention.frais,
                montant_paye=intention.montant,
                devise=intention.devise,
                mode_paiement="MOBILE_MONEY",
                reference_trans=(intention.reference)[:25],
                caissier="MOBILE_MONEY",
                statut="VALIDE",
            )
            _attribuer_numero_recu(intention.ecole, paiement)
            paiement.save()
            intention.paiement = paiement
            intention.statut = "PAYEE"
            intention.reference_operateur = operateur
            intention.save(
                update_fields=["paiement", "statut", "reference_operateur", "updated_at"]
            )
        elif statut in ("ECHEC", "FAILED") and intention.statut != "PAYEE":
            intention.statut = "ECHEC"
            intention.save(update_fields=["statut", "updated_at"])

    return JsonResponse(
        {"ok": True, "reference": intention.reference, "statut": intention.statut}
    )
