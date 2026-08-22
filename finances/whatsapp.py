"""Envoi de notifications WhatsApp pour les paiements validés."""

from __future__ import annotations

import logging
import re
from typing import List, Optional, Tuple

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

MODE_PAIEMENT_LABELS = {
    "ESPECES": "Espèces",
    "MOBILE_MONEY": "Mobile Money",
    "VIREMENT": "Virement",
    "CHEQUE": "Chèque",
}

# Clés autorisées pour les variables de template Meta / texte libre
CLES_CONTEXTE = (
    "parent",
    "eleve",
    "classe",
    "ecole",
    "numero_recu",
    "frais",
    "montant",
    "devise",
    "montant_affiche",
    "mode",
    "date",
)


def normaliser_telephone(numero: Optional[str], indicatif: str = "243") -> Optional[str]:
    """Retourne un numéro international sans +, ou None si invalide."""
    if not numero:
        return None
    digits = re.sub(r"\D", "", str(numero).strip())
    if not digits:
        return None

    indicatif = re.sub(r"\D", "", str(indicatif or "243")) or "243"

    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith(indicatif):
        return digits
    # RDC : 09xxxxxxxx ou 9xxxxxxxx
    if indicatif == "243":
        if digits.startswith("0") and len(digits) == 10:
            return indicatif + digits[1:]
        if len(digits) == 9:
            return indicatif + digits
    if digits.startswith("0"):
        return indicatif + digits[1:]
    if len(digits) >= 9:
        return indicatif + digits
    return None


def _ecole_du_paiement(paiement):
    try:
        return paiement.eleve.classe.ecole
    except AttributeError:
        try:
            return paiement.eleve.eleve.ecole
        except AttributeError:
            return None


def _telephone_tuteur(paiement) -> Tuple[Optional[str], str]:
    """Retourne (numéro brut, nom du parent)."""
    try:
        tuteur = paiement.eleve.eleve.titeur
    except AttributeError:
        return None, ""
    if not tuteur:
        return None, ""
    nom = " ".join(
        p for p in [tuteur.prenom, tuteur.nom, getattr(tuteur, "Post_nom", "")] if p
    ).strip()
    tel = (tuteur.telephone or "").strip() or (tuteur.telephone2 or "").strip()
    return tel or None, nom


def construire_contexte_message(paiement) -> dict:
    ecole = _ecole_du_paiement(paiement)
    inscription = paiement.eleve
    eleve = getattr(inscription, "eleve", None)
    nom_eleve = ""
    if eleve:
        nom_eleve = " ".join(
            p
            for p in [
                getattr(eleve, "prenom", ""),
                getattr(eleve, "nom", ""),
                getattr(eleve, "Post_nom", ""),
            ]
            if p
        ).strip()

    _, parent = _telephone_tuteur(paiement)
    devise = ""
    if getattr(paiement, "devise", None):
        devise = str(paiement.devise.devise)
    montant = paiement.montant_paye
    montant_str = f"{montant:,.2f}".replace(",", " ") if montant is not None else "—"

    # Afficher aussi le montant d'origine si conversion
    if paiement.montant_origine is not None and paiement.taux_change:
        montant_affiche = (
            f"{paiement.montant_origine:,.2f}".replace(",", " ")
            + " CDF"
            + f" (→ {montant_str} {devise})"
        )
    else:
        montant_affiche = f"{montant_str} {devise}".strip()

    date_val = getattr(paiement, "date_encodage", None) or timezone.now()
    if hasattr(date_val, "astimezone"):
        try:
            date_val = timezone.localtime(date_val)
        except Exception:
            pass
    date_str = date_val.strftime("%d/%m/%Y %H:%M") if date_val else ""

    frais_libelle = ""
    try:
        frais_libelle = paiement.frais.type_frais.libelle
    except AttributeError:
        frais_libelle = str(paiement.frais) if paiement.frais_id else ""

    classe = ""
    try:
        classe = str(inscription.classe.classe)
    except AttributeError:
        pass

    return {
        "parent": parent or "Parent",
        "eleve": nom_eleve or "Élève",
        "classe": classe or "—",
        "ecole": ecole.ecole if ecole else "École",
        "numero_recu": paiement.numero_recu or "",
        "frais": frais_libelle,
        "montant": montant_str,
        "devise": devise,
        "montant_affiche": montant_affiche,
        "mode": MODE_PAIEMENT_LABELS.get(
            paiement.mode_paiement, paiement.mode_paiement or ""
        ),
        "date": date_str,
    }


def contexte_test(ecole) -> dict:
    """Contexte factice pour tester un template Meta sans paiement réel."""
    return {
        "parent": "Parent Test",
        "eleve": "Élève Test",
        "classe": "6ème A",
        "ecole": ecole.ecole if ecole else "École",
        "numero_recu": "TEST-0001",
        "frais": "Minerval",
        "montant": "50.00",
        "devise": "USD",
        "montant_affiche": "50.00 USD",
        "mode": "Espèces",
        "date": timezone.localtime(timezone.now()).strftime("%d/%m/%Y %H:%M"),
    }


def formater_message(modele: str, contexte: dict) -> str:
    texte = modele or ""
    for cle, valeur in contexte.items():
        texte = texte.replace("{" + cle + "}", str(valeur if valeur is not None else ""))
    return texte.strip()


def parser_cles_template(config) -> List[str]:
    from .models import ConfigWhatsApp

    brut = (getattr(config, "template_variables", None) or "").strip()
    if not brut:
        brut = ConfigWhatsApp.TEMPLATE_VARS_DEFAUT
    cles = []
    for part in brut.split(","):
        cle = part.strip().lower().replace("{", "").replace("}", "")
        if cle and cle in CLES_CONTEXTE:
            cles.append(cle)
    return cles or list(ConfigWhatsApp.TEMPLATE_VARS_DEFAUT.split(","))


def valeurs_template(config, contexte: dict) -> List[str]:
    """Valeurs textuelles pour {{1}}, {{2}}, … (Meta limite ~1024 car. / param)."""
    valeurs = []
    for cle in parser_cles_template(config):
        val = str(contexte.get(cle) or "—").strip() or "—"
        # Meta interdit certains sauts de ligne / tabs dans les params
        val = re.sub(r"[\t\n\r]+", " ", val)
        if len(val) > 1024:
            val = val[:1021] + "..."
        valeurs.append(val)
    return valeurs


def get_config_pour_ecole(ecole):
    """Config WhatsApp de l'école si définie, sinon le compte central."""
    from .models import ConfigWhatsApp

    return ConfigWhatsApp.charger_pour_ecole(ecole)


def _envoyer_ultramsg(config, telephone: str, message: str) -> Tuple[bool, str, str]:
    instance = (config.instance_id or "").strip()
    token = (config.api_token or "").strip()
    if not instance or not token:
        return False, "", "Instance ID ou token Ultramsg manquant."

    base = (config.api_url or "").strip().rstrip("/")
    if not base:
        base = f"https://api.ultramsg.com/{instance}"
    url = f"{base}/messages/chat"
    try:
        resp = requests.post(
            url,
            data={"token": token, "to": f"+{telephone}", "body": message},
            timeout=getattr(settings, "WHATSAPP_TIMEOUT", 20),
        )
        body = resp.text[:2000]
        if resp.ok:
            return True, body, ""
        return False, body, f"HTTP {resp.status_code}"
    except requests.RequestException as exc:
        return False, "", str(exc)


def _param_texte(valeur, max_len=1024) -> str:
    val = str(valeur if valeur is not None else "—").strip() or "—"
    val = re.sub(r"[\t\n\r]+", " ", val)
    if len(val) > max_len:
        val = val[: max_len - 3] + "..."
    return val


def nom_template(config, kind: str) -> str:
    """Nom du modèle Meta/Bird pour un cas d'usage."""
    kind = (kind or "paiement").lower()
    if kind == "paiement":
        return (getattr(config, "template_meta", None) or "").strip() or getattr(
            settings, "WHATSAPP_META_TEMPLATE_PAIEMENT", "recu_paiement"
        )
    if kind == "relance":
        return (getattr(config, "template_relance", None) or "").strip() or getattr(
            settings, "WHATSAPP_META_TEMPLATE_RELANCE", "relance_minerval"
        )
    if kind == "annonce":
        return (getattr(config, "template_annonce", None) or "").strip() or getattr(
            settings, "WHATSAPP_META_TEMPLATE_ANNONCE", "annonce_ecole"
        )
    if kind == "otp":
        return (getattr(config, "template_otp", None) or "").strip() or getattr(
            settings, "WHATSAPP_META_TEMPLATE_OTP", "code_verification"
        )
    return (getattr(config, "template_meta", None) or "").strip()


def langue_template(config) -> str:
    return (
        (getattr(config, "template_langue", None) or "").strip()
        or getattr(settings, "WHATSAPP_META_LANGUAGE", "fr")
        or "fr"
    )


def _construire_payload_meta_template(
    telephone: str,
    template_name: str,
    langue: str,
    body_params: List[str],
) -> dict:
    params = [{"type": "text", "text": _param_texte(v)} for v in body_params]
    template_obj = {
        "name": template_name,
        "language": {"code": langue or "fr"},
    }
    if params:
        template_obj["components"] = [
            {
                "type": "body",
                "parameters": params,
            }
        ]
    return {
        "messaging_product": "whatsapp",
        "to": telephone,
        "type": "template",
        "template": template_obj,
    }


def envoyer_meta_template(
    config,
    telephone: str,
    template_name: str,
    body_params: List[str],
    *,
    language: Optional[str] = None,
) -> Tuple[bool, str, str]:
    """Envoie un template Meta Cloud API (body {{1}}, {{2}}, …)."""
    phone_id = (config.instance_id or "").strip()
    token = (config.api_token or "").strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    if not phone_id or not token:
        return False, "", "Phone Number ID ou token Meta manquant."
    if not (template_name or "").strip():
        return False, "", "Nom de template Meta manquant."

    base = (config.api_url or "").strip().rstrip("/")
    if not base:
        version = getattr(settings, "WHATSAPP_META_API_VERSION", "v19.0")
        base = f"https://graph.facebook.com/{version}/{phone_id}"
    url = f"{base}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = _construire_payload_meta_template(
        telephone,
        template_name.strip(),
        language or langue_template(config),
        body_params or [],
    )
    try:
        resp = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=getattr(settings, "WHATSAPP_TIMEOUT", 20),
        )
        body = resp.text[:2000]
        if resp.ok:
            return True, body, ""
        return False, body, f"HTTP {resp.status_code}: {body}"
    except requests.RequestException as exc:
        return False, "", str(exc)


def _envoyer_meta(
    config, telephone: str, message: str, contexte: Optional[dict] = None
) -> Tuple[bool, str, str]:
    template = nom_template(config, "paiement")
    if template:
        if contexte is None:
            contexte = {}
        return envoyer_meta_template(
            config,
            telephone,
            template,
            valeurs_template(config, contexte),
            language=langue_template(config),
        )
    phone_id = (config.instance_id or "").strip()
    token = (config.api_token or "").strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    if not phone_id or not token:
        return False, "", "Phone Number ID ou token Meta manquant."

    base = (config.api_url or "").strip().rstrip("/")
    if not base:
        version = getattr(settings, "WHATSAPP_META_API_VERSION", "v19.0")
        base = f"https://graph.facebook.com/{version}/{phone_id}"
    url = f"{base}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": telephone,
        "type": "text",
        "text": {"preview_url": False, "body": message},
    }
    try:
        resp = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=getattr(settings, "WHATSAPP_TIMEOUT", 20),
        )
        body = resp.text[:2000]
        if resp.ok:
            return True, body, ""
        return False, body, f"HTTP {resp.status_code}: {body}"
    except requests.RequestException as exc:
        return False, "", str(exc)


def envoyer_otp_meta(config, telephone: str, code: str) -> Tuple[bool, str, str]:
    """OTP via template Meta code_verification ({{1}} = code)."""
    return envoyer_meta_template(
        config,
        telephone,
        nom_template(config, "otp"),
        [str(code).strip()],
        language=langue_template(config),
    )


def envoyer_relance_meta(config, contexte: dict, telephone: str) -> Tuple[bool, str, str]:
    """Template relance_minerval : ecole, parent, eleve, classe, frais, montant."""
    ordre = ("ecole", "parent", "eleve", "classe", "frais", "montant_affiche")
    params = [_param_texte(contexte.get(cle)) for cle in ordre]
    return envoyer_meta_template(
        config,
        telephone,
        nom_template(config, "relance"),
        params,
        language=langue_template(config),
    )


def envoyer_annonce_meta(config, contexte: dict, telephone: str) -> Tuple[bool, str, str]:
    """Template annonce_ecole : ecole, parent, texte, cible."""
    ordre = ("ecole", "parent", "texte", "cible")
    params = [_param_texte(contexte.get(cle)) for cle in ordre]
    return envoyer_meta_template(
        config,
        telephone,
        nom_template(config, "annonce"),
        params,
        language=langue_template(config),
    )


def provider_effectif(config) -> str:
    """Respecte le fournisseur choisi dans la config ; Bird n'est pas imposé si Meta est sélectionné."""
    provider = (getattr(config, "provider", None) or "LOG").upper()
    if provider == "LOG":
        return "LOG"
    if provider in ("META", "ULTRAMSG", "BIRD"):
        return provider
    if (getattr(settings, "BIRD_API_KEY", "") or "").strip():
        return "BIRD"
    return provider


def _envoyer_bird(
    config, telephone: str, contexte: Optional[dict] = None
) -> Tuple[bool, str, str]:
    from ds.bird import BirdError, bird_configure, envoyer_paiement_whatsapp

    if not bird_configure():
        return False, "", "BIRD_API_KEY manquant dans le fichier .env."
    slug = (getattr(config, "template_meta", None) or "").strip() or None
    langue = (getattr(config, "template_langue", None) or "").strip() or None
    defaut = getattr(settings, "BIRD_WHATSAPP_PAIEMENT_TEMPLATE", "bird_delivery_update")
    if not slug or slug in ("bird_delivery_update", "bird_otp", defaut):
        langue = getattr(settings, "BIRD_WHATSAPP_LANGUAGE", "en") or "en"
    try:
        msg_id, status = envoyer_paiement_whatsapp(
            telephone, contexte or {}, slug=slug, language=langue
        )
        return True, f"id={msg_id} status={status}", ""
    except BirdError as exc:
        detail = ""
        if getattr(exc, "payload", None):
            detail = str(exc.payload)[:2000]
        return False, detail, str(exc)


def _envoyer_via_provider(
    config, telephone: str, message: str, contexte: Optional[dict] = None
) -> Tuple[bool, str, str]:
    provider = provider_effectif(config)
    if provider == "LOG":
        extra = ""
        if contexte and (config.template_meta or "").strip():
            extra = " | vars=" + ",".join(valeurs_template(config, contexte))
        logger.info("WhatsApp [LOG] → +%s : %s%s", telephone, message[:200], extra)
        return True, "mode=LOG" + extra, ""
    if provider == "BIRD":
        return _envoyer_bird(config, telephone, contexte=contexte)
    if provider == "ULTRAMSG":
        return _envoyer_ultramsg(config, telephone, message)
    if provider == "META":
        return _envoyer_meta(config, telephone, message, contexte=contexte)
    return False, "", f"Fournisseur inconnu : {provider}"


def resume_envoi_bird(config, contexte: dict) -> str:
    slug = (config.template_meta or "").strip() or getattr(
        settings, "BIRD_WHATSAPP_PAIEMENT_TEMPLATE", "bird_delivery_update"
    )
    langue = (getattr(config, "template_langue", None) or "").strip() or getattr(
        settings, "BIRD_WHATSAPP_LANGUAGE", "en"
    )
    return (
        f"Template Bird : {slug} ({langue})\n"
        f"ref = {contexte.get('numero_recu') or '—'}\n"
        f"date = {contexte.get('date') or '—'}"
    )


def resume_envoi_meta(config, contexte: dict) -> str:
    """Texte journalisé décrivant le template + variables envoyées."""
    nom = nom_template(config, "paiement")
    if not nom:
        return formater_message(config.modele_effectif(), contexte)
    langue = langue_template(config)
    cles = parser_cles_template(config)
    vals = valeurs_template(config, contexte)
    lignes = [f"Template Meta : {nom} ({langue})"]
    for i, (cle, val) in enumerate(zip(cles, vals), start=1):
        lignes.append(f"{{{{{i}}}}} ({cle}) = {val}")
    return "\n".join(lignes)


def notifier_communication_whatsapp(communication) -> dict:
    """
    Envoie l'annonce école → parents via WhatsApp (template annonce_ecole).
    Retourne {envoyes, echecs, ignores}.
    """
    from utilisateur.security import telephone_utilisateur

    from .models import NotificationWhatsApp

    ecole = communication.ecole
    config = get_config_pour_ecole(ecole)
    stats = {"envoyes": 0, "echecs": 0, "ignores": 0}
    if config is None or not config.actif:
        return stats

    canal = provider_effectif(config)
    texte = f"{communication.sujet}\n{communication.contenu}".strip()
    cible = communication.libelle_cible
    lectures = communication.lectures.select_related("parent", "parent__tuteur").all()

    for lecture in lectures:
        parent = lecture.parent
        parent_nom = ""
        if parent:
            parent_nom = (
                getattr(parent, "nom_complet", None)
                or f"{getattr(parent, 'prenom', '')} {getattr(parent, 'last_name', '')}".strip()
            )
        contexte = {
            "ecole": ecole.ecole if ecole else "École",
            "parent": parent_nom or "Parent",
            "texte": texte,
            "cible": cible,
        }
        tel_e164 = telephone_utilisateur(parent) if parent else ""
        telephone = normaliser_telephone(
            tel_e164, getattr(config, "indicatif_pays", None) or "243"
        )
        message = (
            f"Template Meta : {nom_template(config, 'annonce')} ({langue_template(config)})\n"
            f"ecole={contexte['ecole']}\nparent={contexte['parent']}\n"
            f"cible={contexte['cible']}\ntexte={_param_texte(texte, 200)}"
        )
        if not telephone:
            NotificationWhatsApp.objects.create(
                ecole=ecole,
                paiement=None,
                destinataire="",
                message=message,
                statut="IGNORE",
                provider=canal,
                erreur="Aucun numéro WhatsApp pour ce parent.",
            )
            stats["ignores"] += 1
            continue

        if canal == "META":
            ok, reponse, erreur = envoyer_annonce_meta(config, contexte, telephone)
        elif canal == "LOG":
            logger.info("WhatsApp [LOG] annonce → +%s : %s", telephone, texte[:200])
            ok, reponse, erreur = True, "mode=LOG", ""
        else:
            # Bird / Ultramsg : message texte libre (hors template Meta)
            ok, reponse, erreur = _envoyer_via_provider(
                config, telephone, texte[:1500], contexte=contexte
            )

        NotificationWhatsApp.objects.create(
            ecole=ecole,
            paiement=None,
            destinataire=f"+{telephone}",
            message=message,
            statut="ENVOYE" if ok else "ECHEC",
            provider=canal,
            reponse_api=reponse or "",
            erreur=erreur or "",
        )
        if ok:
            stats["envoyes"] += 1
        else:
            stats["echecs"] += 1
            logger.warning(
                "WhatsApp annonce échec com=%s → %s : %s",
                communication.pk,
                telephone,
                erreur,
            )
    return stats


def notifier_paiement_whatsapp(paiement, force: bool = False):
    """
    Envoie un WhatsApp au tuteur pour un paiement VALIDÉ.
    Ne renvoie pas si une notif ENVOYE existe déjà (sauf force=True).
    Ne bloque jamais le flux paiement (exceptions capturées).
    """
    from .models import NotificationWhatsApp

    if getattr(paiement, "statut", None) != "VALIDE":
        return None

    ecole = _ecole_du_paiement(paiement)
    if ecole is None:
        return None

    config = get_config_pour_ecole(ecole)
    if config is None or not config.actif:
        return None

    if not force and NotificationWhatsApp.objects.filter(
        paiement=paiement, statut="ENVOYE"
    ).exists():
        return None

    tel_brut, _ = _telephone_tuteur(paiement)
    telephone = normaliser_telephone(tel_brut, config.indicatif_pays)
    contexte = construire_contexte_message(paiement)
    canal = provider_effectif(config)

    if canal == "META":
        message = resume_envoi_meta(config, contexte)
    elif canal == "BIRD":
        message = resume_envoi_bird(config, contexte)
    else:
        message = formater_message(config.modele_effectif(), contexte)

    if not telephone:
        notif = NotificationWhatsApp.objects.create(
            ecole=ecole,
            paiement=paiement,
            destinataire="",
            message=message,
            statut="IGNORE",
            provider=canal,
            erreur="Aucun numéro de téléphone valide pour le tuteur.",
        )
        return notif

    ok, reponse, erreur = _envoyer_via_provider(
        config, telephone, message, contexte=contexte
    )
    notif = NotificationWhatsApp.objects.create(
        ecole=ecole,
        paiement=paiement,
        destinataire=f"+{telephone}",
        message=message,
        statut="ENVOYE" if ok else "ECHEC",
        provider=canal,
        reponse_api=reponse or "",
        erreur=erreur or "",
    )
    if not ok:
        logger.warning(
            "WhatsApp échec paiement %s → %s : %s",
            paiement.numero_recu,
            telephone,
            erreur,
        )
    return notif
