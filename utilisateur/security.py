"""Contrôles de sécurité : OTP, verrouillage, journaux, empreinte d'appareil."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone

MSG_AUTH_GENERIQUE = "Identifiant ou mot de passe incorrect."
MSG_INSCRIPTION_GENERIQUE = (
    "Les informations saisies ne correspondent pas aux données de l'établissement. "
    "Vérifiez votre saisie ou contactez l'école."
)
MSG_COMPTE_VERROUILLE = MSG_AUTH_GENERIQUE
MSG_CODE_INVALIDE = "Code incorrect ou expiré. Demandez un nouveau code si besoin."
MSG_CONTACT_MANQUANT = (
    "L'etablissement n'a pas enregistre de numero WhatsApp pour cette fiche. "
    "Contactez l'ecole pour activer votre compte."
)

MATRICULE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9\-]{2,19}$")

SESSION_SIGNUP = "ds_signup_pending"
SESSION_MFA = "ds_mfa_pending"
SESSION_RESET = "ds_reset_pending"
SESSION_CONNEXION_ID = "ds_session_connexion_id"
DUREE_ACTUALISATION_SEEN = timedelta(seconds=120)

ROLES_MFA = frozenset({
    "MANAGER",
    "DIRECTEUR",
    "ENSEIGNANT",
    "PROFESSEUR",
    "TRESORIE",
    "CAISSIER",
    "PARENT",
})


def client_ip(request):
    remote = request.META.get("REMOTE_ADDR") or ""
    trusted = getattr(settings, "TRUSTED_PROXIES", None) or ("127.0.0.1", "::1")
    if remote in trusted:
        forwarded = (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
        if forwarded:
            return forwarded
    return remote


def user_agent(request, limite=280):
    return (request.META.get("HTTP_USER_AGENT") or "")[:limite]


def _secret():
    return (getattr(settings, "SECRET_KEY", "") or "ds").encode("utf-8")


def hasher_code(code):
    return hmac.new(_secret(), str(code).encode("utf-8"), hashlib.sha256).hexdigest()


def codes_egaux(code_saisi, code_hash):
    if not code_saisi or not code_hash:
        return False
    return hmac.compare_digest(hasher_code(code_saisi.strip()), code_hash)


def generer_code(n=6):
    return f"{secrets.randbelow(10 ** n):0{n}d}"


def masquer_telephone(numero):
    digits = re.sub(r"\D", "", numero or "")
    if len(digits) < 6:
        return "***"
    return f"+{digits[:4]}***{digits[-3:]}"


def telephone_e164(numero, indicatif="243"):
    from finances.whatsapp import normaliser_telephone

    digits = normaliser_telephone(numero, indicatif)
    if not digits:
        return ""
    return f"+{digits}"


def telephone_fiche(cible):
    if cible is None:
        return ""
    for attr in ("telephone", "telephone2", "telephone1"):
        brut = (getattr(cible, attr, None) or "").strip()
        if brut:
            tel = telephone_e164(brut)
            if tel:
                return tel
    return ""


def telephone_utilisateur(user):
    """Numéro WhatsApp du compte : profil, fiche métier, puis téléphone de l'école."""
    if not user:
        return ""
    propre = telephone_e164(getattr(user, "telephone", None) or "")
    if propre:
        return propre
    if getattr(user, "tuteur_id", None) and getattr(user, "tuteur", None):
        tel = telephone_fiche(user.tuteur)
        if tel:
            return tel
    try:
        tel = telephone_fiche(user.personnel)
        if tel:
            return tel
    except Exception:
        pass
    ecole = getattr(user, "ecole", None)
    tel = telephone_fiche(ecole)
    if tel:
        return tel
    return ""


def trouver_utilisateur_pour_reset(identifiant):
    """Compte actif correspondant à l'identifiant ou au numéro WhatsApp."""
    from django.db.models import Q

    from .models import Utilisateur

    ident = (identifiant or "").strip()
    if not ident:
        return None
    user = Utilisateur.objects.filter(is_active=True, username__iexact=ident).first()
    if user:
        return user
    digits = re.sub(r"\D", "", ident)
    if len(digits) < 9:
        return None
    suffixe = digits[-9:]
    candidats = Utilisateur.objects.filter(is_active=True).filter(
        Q(telephone__icontains=suffixe) | Q(tuteur__telephone__icontains=suffixe)
    )
    for candidat in candidats.select_related("tuteur")[:8]:
        tel = telephone_utilisateur(candidat)
        if tel and re.sub(r"\D", "", tel).endswith(suffixe):
            return candidat
    return None


def empreinte_appareil(request):
    brut = f"{user_agent(request).casefold()}|{client_ip(request)}"
    return hashlib.sha256(brut.encode("utf-8")).hexdigest()


def lockout_cle(request, username):
    ident = (username or "").strip().casefold()
    return f"{client_ip(request)}|{ident}"[:190]


def est_verrouille(request, username):
    from .models import VerrouillageConnexion

    cle = lockout_cle(request, username)
    row = VerrouillageConnexion.objects.filter(cle=cle).first()
    if not row or not row.verrouille_jusquau:
        return False
    if row.verrouille_jusquau <= timezone.now():
        row.echecs = 0
        row.verrouille_jusquau = None
        row.save(update_fields=["echecs", "verrouille_jusquau"])
        return False
    return True


def enregistrer_echec_connexion(request, username):
    from .models import VerrouillageConnexion

    limite = int(getattr(settings, "LOGIN_LOCKOUT_LIMIT", 5))
    minutes = int(getattr(settings, "LOGIN_LOCKOUT_MINUTES", 15))
    cle = lockout_cle(request, username)
    row, _ = VerrouillageConnexion.objects.get_or_create(cle=cle)
    row.echecs = (row.echecs or 0) + 1
    if row.echecs >= limite:
        row.verrouille_jusquau = timezone.now() + timedelta(minutes=minutes)
    row.save(update_fields=["echecs", "verrouille_jusquau", "updated_at"])
    journaliser(
        request,
        action="CONNEXION_ECHOUEE",
        ressource="auth",
        extra={"username": (username or "")[:80]},
    )
    return row


def reinitialiser_echecs(request, username):
    from .models import VerrouillageConnexion

    VerrouillageConnexion.objects.filter(cle=lockout_cle(request, username)).delete()


def doit_mfa(user):
    """Second facteur WhatsApp à chaque connexion, sauf compte élève."""
    if not getattr(settings, "MFA_WHATSAPP_ACTIF", False):
        return False
    if not getattr(user, "pk", None):
        return False
    return getattr(user, "role", None) != "ELEVE"


def journaliser(request, action, ressource="", identifiant="", ecole=None, extra=None, user=None):
    from .models import JournalAcces

    user = user if user is not None else getattr(request, "user", None)
    if user is not None and not getattr(user, "is_authenticated", False):
        user = None
    if ecole is None and user is not None:
        ecole = getattr(user, "ecole", None)
    JournalAcces.objects.create(
        utilisateur=user if getattr(user, "pk", None) else None,
        action=action,
        ressource=(ressource or "")[:80],
        identifiant=str(identifiant or "")[:64],
        ecole=ecole,
        ip=client_ip(request) or None,
        user_agent=user_agent(request),
        extra=extra,
    )
    if action in {"CONSULTATION_ELEVE", "BULLETIN"} and user is not None:
        _alerter_volume(request, user, ecole)


def _alerter_volume(request, user, ecole):
    from .models import JournalAcces

    seuil = int(getattr(settings, "AUDIT_VOLUME_SEUIL", 40))
    fenetre = int(getattr(settings, "AUDIT_VOLUME_MINUTES", 10))
    depuis = timezone.now() - timedelta(minutes=fenetre)
    n = JournalAcces.objects.filter(
        utilisateur=user,
        action__in=("CONSULTATION_ELEVE", "BULLETIN"),
        created_at__gte=depuis,
    ).count()
    if n >= seuil:
        deja = JournalAcces.objects.filter(
            utilisateur=user,
            action="ALERTE_VOLUME",
            created_at__gte=depuis,
        ).exists()
        if not deja:
            JournalAcces.objects.create(
                utilisateur=user,
                action="ALERTE_VOLUME",
                ressource="eleve",
                identifiant=str(n),
                ecole=ecole,
                ip=client_ip(request) or None,
                user_agent=user_agent(request),
                extra={"consultations": n, "minutes": fenetre},
            )


def contact_telephone_fiche(profil, cible):
    """Numero WhatsApp deja enregistre par l'ecole (jamais celui saisi par le visiteur)."""
    if cible is None:
        return ""
    if profil == "ELEVE":
        return telephone_fiche(getattr(cible, "titeur", None))
    return telephone_fiche(cible)


def envoyer_code_whatsapp(destinataire, code):
    """Envoie l'OTP WhatsApp. Retourne (ok, erreur). En DEBUG le code est journalisé si l'API échoue."""
    import logging

    logger = logging.getLogger(__name__)
    if not destinataire:
        return False, "Aucun numéro WhatsApp."

    digits = re.sub(r"\D", "", str(destinataire))
    meta_erreur = ""
    try:
        from finances.models import ConfigWhatsApp
        from finances.whatsapp import (
            envoyer_otp_meta,
            normaliser_telephone,
            provider_effectif,
        )

        config = ConfigWhatsApp.charger_centrale()
        if config and config.actif and provider_effectif(config) == "META":
            telephone = normaliser_telephone(digits, config.indicatif_pays) or digits
            ok, _reponse, erreur = envoyer_otp_meta(config, telephone, code)
            if ok:
                return True, ""
            meta_erreur = erreur or "Échec Meta OTP"
            logger.warning("Envoi OTP Meta échoué vers %s : %s", destinataire, meta_erreur)
    except Exception as meta_exc:
        meta_erreur = str(meta_exc)
        logger.warning("Envoi OTP Meta échoué vers %s : %s", destinataire, meta_exc)

    try:
        from ds.bird import bird_configure, envoyer_otp_whatsapp

        if bird_configure():
            envoyer_otp_whatsapp(destinataire, code)
            return True, ""
    except Exception as exc:
        logger.warning("Envoi OTP WhatsApp échoué vers %s : %s", destinataire, exc)
        if getattr(settings, "DEBUG", False):
            logger.info(
                "Code MFA (DEBUG) pour %s : %s",
                masquer_telephone(destinataire),
                code,
            )
        parties = [p for p in (meta_erreur, str(exc)[:240]) if p]
        return False, " | ".join(parties)[:400]

    if meta_erreur:
        return False, meta_erreur[:400]
    return False, "Aucun canal WhatsApp OTP disponible (Meta / Bird)."


def payload_otp(code, extra=None):
    ttl = int(getattr(settings, "OTP_TTL_MINUTES", 10))
    data = {
        "code_hash": hasher_code(code),
        "expires": (timezone.now() + timedelta(minutes=ttl)).isoformat(),
        "attempts": 0,
        "sent_at": timezone.now().isoformat(),
        "resend_count": 0,
    }
    if extra:
        data.update(extra)
    return data


def otp_peut_renvoyer(payload):
    """Retourne (ok, message_erreur). Cooldown + plafond de renvois."""
    if not payload:
        return False, MSG_CODE_INVALIDE
    cooldown = int(getattr(settings, "OTP_RENVOI_COOLDOWN_SECONDS", 60) or 60)
    max_renvois = int(getattr(settings, "OTP_RENVOI_MAX", 5) or 5)
    try:
        sent_at = datetime.fromisoformat(payload.get("sent_at") or "")
        if timezone.is_naive(sent_at):
            sent_at = timezone.make_aware(sent_at, timezone.get_current_timezone())
    except (TypeError, ValueError):
        sent_at = None
    if sent_at is not None:
        ecoule = (timezone.now() - sent_at).total_seconds()
        if ecoule < cooldown:
            reste = max(1, int(cooldown - ecoule))
            return False, f"Patientez {reste} s avant de renvoyer un code."
    count = int(payload.get("resend_count") or 0)
    if count >= max_renvois:
        return False, "Nombre maximal de renvois atteint. Recommencez la procédure."
    return True, ""


def otp_encore_valide(payload):
    if not payload:
        return False
    try:
        expire = datetime.fromisoformat(payload["expires"])
    except (KeyError, TypeError, ValueError):
        return False
    if timezone.is_naive(expire):
        expire = timezone.make_aware(expire, timezone.get_current_timezone())
    return expire > timezone.now()


def verifier_otp_session(payload, code_saisi):
    max_essais = int(getattr(settings, "OTP_MAX_ATTEMPTS", 5))
    if not payload or not otp_encore_valide(payload):
        return False, MSG_CODE_INVALIDE
    if int(payload.get("attempts") or 0) >= max_essais:
        return False, MSG_CODE_INVALIDE
    payload["attempts"] = int(payload.get("attempts") or 0) + 1
    if not codes_egaux(code_saisi, payload.get("code_hash")):
        return False, MSG_CODE_INVALIDE
    return True, ""


def notifier_nouvel_appareil(request, user):
    from .models import AppareilConnu

    tel = telephone_utilisateur(user)
    if not user:
        return
    empreinte = empreinte_appareil(request)
    connu = AppareilConnu.objects.filter(utilisateur=user, empreinte=empreinte).first()
    if connu:
        connu.save(update_fields=["dernier_vu"])
        return
    premier = not AppareilConnu.objects.filter(utilisateur=user).exists()
    AppareilConnu.objects.create(
        utilisateur=user,
        empreinte=empreinte,
        libelle=(user_agent(request) or "Appareil")[:200],
    )
    if premier:
        return
    journaliser(
        request,
        action="NOUVEL_APPAREIL",
        ressource="auth",
        extra={"telephone": masquer_telephone(tel)} if tel else None,
        user=user,
    )


def valider_matricule(valeur):
    valeur = (valeur or "").strip()
    if not MATRICULE_RE.match(valeur):
        return ""
    return valeur


def duree_inactivite_session():
    secondes = int(getattr(settings, "SESSION_IDLE_SECONDS", 900) or 900)
    return timedelta(seconds=max(60, secondes))


def cloturer_sessions_inactives(utilisateur=None, maintenant=None):
    """Ferme les sessions sans activité depuis SESSION_IDLE_SECONDS (défaut 15 min)."""
    from django.contrib.sessions.models import Session as DjangoSession

    from .models import SessionConnexion

    maintenant = maintenant or timezone.now()
    seuil = maintenant - duree_inactivite_session()
    qs = SessionConnexion.objects.filter(ended_at__isnull=True, last_seen__lt=seuil)
    if utilisateur is not None:
        qs = qs.filter(utilisateur=utilisateur)
    cles = [cle for cle in qs.values_list("cle_session", flat=True) if cle]
    n = qs.update(ended_at=maintenant)
    if cles:
        DjangoSession.objects.filter(session_key__in=cles).delete()
    return n


def ouvrir_session_connexion(request, user, via_mfa=False):
    """Enregistre une session à chaque connexion réussie (après auth_login)."""
    from .models import SessionConnexion

    cloturer_sessions_inactives(utilisateur=user)
    ancien_id = request.session.get(SESSION_CONNEXION_ID)
    if ancien_id:
        SessionConnexion.objects.filter(pk=ancien_id, ended_at__isnull=True).update(
            ended_at=timezone.now(),
            last_seen=timezone.now(),
        )
    if not request.session.session_key:
        request.session.create()
    cle = request.session.session_key or ""
    maintenant = timezone.now()
    SessionConnexion.objects.filter(
        utilisateur=user,
        cle_session=cle,
        ended_at__isnull=True,
    ).update(ended_at=maintenant, last_seen=maintenant)
    obj = SessionConnexion.objects.create(
        utilisateur=user,
        cle_session=cle,
        ip=client_ip(request) or None,
        user_agent=user_agent(request),
        mfa=bool(via_mfa),
        last_seen=maintenant,
    )
    request.session[SESSION_CONNEXION_ID] = obj.pk
    request.session.modified = True
    return obj


def fermer_session_connexion(request, revoquer=False):
    from .models import SessionConnexion

    sid = request.session.get(SESSION_CONNEXION_ID)
    if not sid:
        return
    SessionConnexion.objects.filter(pk=sid, ended_at__isnull=True).update(
        ended_at=timezone.now(),
        revoquee=revoquer,
        last_seen=timezone.now(),
    )


def revoquer_session_connexion(session_obj):
    """Invalide une session (déconnexion à distance)."""
    from django.contrib.sessions.models import Session as DjangoSession

    maintenant = timezone.now()
    session_obj.revoquee = True
    session_obj.ended_at = maintenant
    session_obj.last_seen = maintenant
    session_obj.save(update_fields=["revoquee", "ended_at", "last_seen"])
    if session_obj.cle_session:
        DjangoSession.objects.filter(session_key=session_obj.cle_session).delete()


def actualiser_session_connexion(request):
    """Met à jour last_seen. Retourne 'inactivite' / 'fermee' si logout, sinon None."""
    from django.contrib.auth import logout as auth_logout

    from .models import SessionConnexion

    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return None
    sid = request.session.get(SESSION_CONNEXION_ID)
    if not sid:
        return None
    maintenant = timezone.now()
    cloturer_sessions_inactives(utilisateur=user, maintenant=maintenant)
    obj = SessionConnexion.objects.filter(pk=sid, utilisateur=user).first()
    if obj is None or obj.revoquee or obj.ended_at:
        motif = "inactivite" if obj and obj.ended_at and not obj.revoquee else "fermee"
        auth_logout(request)
        return motif
    if (maintenant - (obj.last_seen or obj.created_at)) >= duree_inactivite_session():
        SessionConnexion.objects.filter(pk=obj.pk, ended_at__isnull=True).update(
            ended_at=maintenant,
        )
        auth_logout(request)
        return "inactivite"
    if not obj.last_seen or (maintenant - obj.last_seen) >= DUREE_ACTUALISATION_SEEN:
        SessionConnexion.objects.filter(pk=obj.pk).update(last_seen=maintenant)
    return None
