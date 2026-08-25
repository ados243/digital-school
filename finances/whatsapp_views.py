"""Configuration et tests WhatsApp (extraits de finances.views)."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ConfigWhatsAppForm
from .models import ConfigWhatsApp, NotificationWhatsApp
from .tenant import get_user_ecole, paiements_for_ecole


@login_required
def whatsapp_config(request):
    """Configuration WhatsApp centrale + journal des envois."""
    ecole = get_user_ecole(request)
    if not request.user.is_superuser:
        messages.error(request, "Seul un superutilisateur peut configurer WhatsApp.")
        return redirect("finances:dashboard")

    config = ConfigWhatsApp.charger_centrale()

    if request.method == "POST" and request.POST.get("action") == "save_config":
        form = ConfigWhatsAppForm(request.POST, instance=config)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.ecole = None
            obj.save()
            messages.success(request, "Configuration WhatsApp centrale enregistrée.")
            return redirect("finances:whatsapp_config")
    else:
        form = ConfigWhatsAppForm(instance=config)

    from .whatsapp import CLES_CONTEXTE, etat_credentials_meta, parser_cles_template

    notif_qs = NotificationWhatsApp.objects.select_related("paiement", "ecole")
    if not request.user.is_superuser and ecole:
        notif_qs = notif_qs.filter(ecole=ecole)
    notifications = notif_qs.order_by("-date_envoi")[:80]
    mapping_vars = [
        (f"{{{{{i}}}}}", cle)
        for i, cle in enumerate(parser_cles_template(config), start=1)
    ]
    _phone, _tok, cred_statut = etat_credentials_meta(config)
    return render(
        request,
        "finances/whatsapp_config.html",
        {
            "form": form,
            "config": config,
            "notifications": notifications,
            "ecole": ecole,
            "journal_multi_ecoles": request.user.is_superuser,
            "placeholders": " ".join("{" + c + "}" for c in CLES_CONTEXTE),
            "mapping_vars": mapping_vars,
            "meta_cred_statut": cred_statut,
            "meta_phone_id": (config.instance_id or "").strip(),
            "meta_token_enregistre": bool((config.api_token or "").strip()),
            "exemple_template_meta": (
                "Bonjour, paiement reçu pour {{1}}.\n"
                "Montant : {{2}}\n"
                "Reçu : {{3}}\n"
                "Frais : {{4}}\n"
                "Classe : {{5}}\n"
                "Date : {{6}}\n"
                "Merci — Digital School."
            ),
            "exemple_template_bird": (
                "Your order {{ref}} is expected to be delivered on {{date}}."
            ),
        },
    )


@login_required
def whatsapp_test(request):
    """Envoie un message de test au numéro saisi (ou au téléphone de l'école)."""
    ecole = get_user_ecole(request)
    if not request.user.is_superuser:
        messages.error(request, "Seul un superutilisateur peut tester WhatsApp.")
        return redirect("finances:dashboard")
    if request.method != "POST":
        return redirect("finances:whatsapp_config")

    config = ConfigWhatsApp.charger_centrale()
    if not config or not config.actif:
        messages.error(request, "Activez d'abord WhatsApp et enregistrez la configuration centrale.")
        return redirect("finances:whatsapp_config")

    from .whatsapp import (
        contexte_test,
        formater_message,
        normaliser_telephone,
        provider_effectif,
        resume_envoi_bird,
        resume_envoi_meta,
        _envoyer_via_provider,
    )

    tel_brut = (request.POST.get("telephone_test") or "").strip() or (
        getattr(ecole, "telephone1", None) or ""
    )
    telephone = normaliser_telephone(tel_brut, config.indicatif_pays)
    if not telephone:
        messages.error(request, "Numéro de test invalide.")
        return redirect("finances:whatsapp_config")

    contexte = contexte_test(ecole)
    canal = provider_effectif(config)
    if canal == "META":
        message = resume_envoi_meta(config, contexte)
    elif canal == "BIRD":
        message = resume_envoi_bird(config, contexte)
    else:
        message = formater_message(config.modele_effectif(), contexte)

    kind = (request.POST.get("kind") or "paiement").strip().lower()
    if kind == "otp":
        import secrets

        from .whatsapp import envoyer_otp_meta, message_echec_otp, nom_template

        if canal != "META":
            messages.error(
                request,
                "L'OTP WhatsApp utilise Meta. Choisissez le fournisseur Meta, enregistrez, puis relancez le test.",
            )
            return redirect("finances:whatsapp_config")

        code = f"{secrets.randbelow(1_000_000):06d}"
        ok, reponse, erreur = envoyer_otp_meta(config, telephone, code)
        NotificationWhatsApp.objects.create(
            ecole=ecole,
            paiement=None,
            destinataire=f"+{telephone}"[:20],
            message=f"Test OTP {nom_template(config, 'otp')}",
            statut="ENVOYE" if ok else "ECHEC",
            provider="META",
            reponse_api=(reponse or "")[:240],
            erreur=erreur or "",
        )
        if ok:
            messages.success(request, f"Code OTP de test envoyé à +{telephone}.")
        else:
            detail = (erreur or "erreur API")[:500]
            messages.error(
                request,
                f"{message_echec_otp(erreur, nom_template(config, 'otp'))} "
                f"Détail : {detail}",
            )
        return redirect("finances:whatsapp_config")

    ok, reponse, erreur = _envoyer_via_provider(
        config, telephone, message, contexte=contexte
    )
    NotificationWhatsApp.objects.create(
        ecole=ecole,
        paiement=None,
        destinataire=f"+{telephone}",
        message=message,
        statut="ENVOYE" if ok else "ECHEC",
        provider=canal,
        reponse_api=(reponse or "")[:240],
        erreur=erreur or "",
    )
    if ok:
        messages.success(request, f"Message de test envoyé à +{telephone}.")
    else:
        messages.error(request, f"Échec d'envoi : {erreur or 'erreur API'}")
    return redirect("finances:whatsapp_config")


@login_required
def whatsapp_renvoyer(request, pk):
    """Renvoie la notification WhatsApp pour un paiement."""
    ecole = get_user_ecole(request)
    if not request.user.is_superuser:
        messages.error(request, "Seul un superutilisateur peut renvoyer un WhatsApp.")
        return redirect("finances:dashboard")

    paiement = get_object_or_404(paiements_for_ecole(ecole), pk=pk)
    if paiement.statut != "VALIDE":
        messages.error(request, "Seuls les paiements validés peuvent être notifiés.")
        return redirect("finances:whatsapp_config")

    from .whatsapp import notifier_paiement_whatsapp

    notif = notifier_paiement_whatsapp(paiement, force=True)
    if notif is None:
        messages.warning(
            request,
            "Aucune notification envoyée (WhatsApp inactif ou école introuvable).",
        )
    elif notif.statut == "ENVOYE":
        messages.success(request, f"WhatsApp renvoyé pour le reçu {paiement.numero_recu}.")
    elif notif.statut == "IGNORE":
        messages.warning(request, notif.erreur or "Notification ignorée.")
    else:
        messages.error(request, notif.erreur or "Échec d'envoi WhatsApp.")
    return redirect("finances:whatsapp_config")
