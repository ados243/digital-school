"""Client Bird (e-mail transactionnel + WhatsApp) via l'API REST.

Le SDK officiel exige Python 3.10+ ; Digital School tourne en 3.9, d'où
requests + https://eu1.platform.bird.com (clé bk_eu1_…).
"""

from __future__ import annotations

import logging
from email.utils import parseaddr

import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)


def bird_configure():
    cle = (getattr(settings, "BIRD_API_KEY", "") or "").strip()
    return bool(cle)


def _region_host():
    cle = (getattr(settings, "BIRD_API_KEY", "") or "").strip()
    if cle.startswith("bk_us1_"):
        return "https://us1.platform.bird.com"
    return "https://eu1.platform.bird.com"


def _headers():
    return {
        "Authorization": f"Bearer {settings.BIRD_API_KEY.strip()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _parse_expediteur(valeur):
    valeur = (valeur or "").strip()
    if not valeur:
        return {"email": "onboarding@messagebird.dev", "name": "Digital School"}
    nom, email = parseaddr(valeur)
    if not email:
        return {"email": valeur, "name": "Digital School"}
    return {"email": email, "name": nom or "Digital School"}


class BirdError(Exception):
    def __init__(self, message, status=None, payload=None):
        super().__init__(message)
        self.status = status
        self.payload = payload


def envoyer_email_bird(destinataires, sujet, texte, html=None, expediteur=None):
    """Envoie un e-mail transactionnel. Retourne (id, status) ou lève BirdError."""
    if not bird_configure():
        raise BirdError("BIRD_API_KEY n'est pas défini.")
    if isinstance(destinataires, str):
        destinataires = [destinataires]
    to = [{"email": d.strip()} for d in destinataires if (d or "").strip()]
    if not to:
        raise BirdError("Aucun destinataire e-mail.")

    from_obj = _parse_expediteur(
        getattr(settings, "BIRD_FROM_EMAIL", "")
        or expediteur
        or settings.DEFAULT_FROM_EMAIL
    )
    payload = {
        "from": from_obj,
        "to": to,
        "subject": sujet,
        "text": texte or "",
        "category": "transactional",
        "tags": [{"name": "app", "value": "digital-school"}],
    }
    if html:
        payload["html"] = html

    url = f"{_region_host()}/v1/email/messages"
    try:
        resp = requests.post(url, json=payload, headers=_headers(), timeout=20)
    except requests.RequestException as exc:
        raise BirdError(f"Réseau Bird : {exc}") from exc

    if resp.status_code not in (200, 201, 202):
        detail = resp.text[:800]
        logger.warning("Bird e-mail HTTP %s : %s", resp.status_code, detail)
        raise BirdError(f"Bird e-mail HTTP {resp.status_code}: {detail}", status=resp.status_code)
    data = {}
    try:
        data = resp.json()
    except ValueError:
        pass
    return data.get("id"), data.get("status") or "accepted"


def envoyer_whatsapp_bird(to, template, components=None, language=None):
    """Envoie un WhatsApp template (équivalent de client.whatsapp.send)."""
    if not bird_configure():
        raise BirdError("BIRD_API_KEY n'est pas defini.")
    numero = (to or "").strip()
    if numero and not numero.startswith("+"):
        numero = f"+{numero}"
    if not numero:
        raise BirdError("Numero WhatsApp manquant.")

    slug = template if isinstance(template, str) else (template or {}).get("slug")
    if not slug:
        raise BirdError("Template WhatsApp manquant.")

    langue = language or getattr(settings, "BIRD_WHATSAPP_LANGUAGE", "fr") or "fr"
    tpl = {"slug": slug, "language": langue}
    if components:
        tpl["components"] = components

    url = f"{_region_host()}/v1/whatsapp/messages"
    try:
        resp = requests.post(
            url,
            json={"to": numero, "template": tpl},
            headers=_headers(),
            timeout=20,
        )
    except requests.RequestException as exc:
        raise BirdError(f"Reseau Bird : {exc}") from exc

    if resp.status_code not in (200, 201, 202):
        detail = resp.text[:800]
        logger.warning("Bird WhatsApp HTTP %s : %s", resp.status_code, detail)
        raise BirdError(
            f"Bird WhatsApp HTTP {resp.status_code}: {detail}",
            status=resp.status_code,
        )
    data = {}
    try:
        data = resp.json()
    except ValueError:
        pass
    return data.get("id"), data.get("status") or "accepted"


def envoyer_paiement_whatsapp(to, contexte, slug=None, language=None):
    """Recu de paiement. Defaut : bird_delivery_update (ref + date)."""
    slug = slug or getattr(settings, "BIRD_WHATSAPP_PAIEMENT_TEMPLATE", "") or "bird_delivery_update"
    ctx = contexte or {}
    if slug == "bird_delivery_update":
        components = [{
            "type": "body",
            "parameters": [
                {"type": "text", "name": "ref", "text": str(ctx.get("numero_recu") or "-")[:60]},
                {"type": "text", "name": "date", "text": str(ctx.get("date") or "-")[:60]},
            ],
        }]
    else:
        ordre = (
            "parent", "eleve", "classe", "ecole", "numero_recu",
            "frais", "montant_affiche", "mode", "date",
        )
        params = [
            {"type": "text", "name": cle, "text": str(ctx.get(cle) or "-")[:60]}
            for cle in ordre
            if ctx.get(cle)
        ]
        components = [{"type": "body", "parameters": params}] if params else None
    return envoyer_whatsapp_bird(to, slug, components=components, language=language)


class BirdEmailBackend(BaseEmailBackend):
    """Backend Django : tout send_mail() passe par Bird si la clé est définie."""

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        envoyes = 0
        for message in email_messages:
            try:
                html = None
                if getattr(message, "alternatives", None):
                    for contenu, mimetype in message.alternatives:
                        if mimetype == "text/html":
                            html = contenu
                            break
                envoyer_email_bird(
                    list(message.to or []) + list(message.cc or []),
                    message.subject,
                    message.body,
                    html=html,
                    expediteur=message.from_email,
                )
                envoyes += 1
            except BirdError as exc:
                logger.error("Envoi Bird échoué : %s", exc)
                if not self.fail_silently:
                    raise
        return envoyes
