"""Chiffrement léger au repos (Fernet dérivé de SECRET_KEY)."""

from __future__ import annotations

import base64
import hashlib
import logging

from django.conf import settings

logger = logging.getLogger(__name__)

PREFIX = "enc:v1:"


def _fernet():
    from cryptography.fernet import Fernet

    raw = (getattr(settings, "DJANGO_FERNET_KEY", "") or "").strip()
    if raw:
        key = raw.encode("utf-8") if isinstance(raw, str) else raw
        # Accepte une clé Fernet déjà encodée urlsafe
        try:
            return Fernet(key if isinstance(key, bytes) else key.encode())
        except Exception:
            pass
    digest = hashlib.sha256(
        (getattr(settings, "SECRET_KEY", "") or "ds").encode("utf-8")
    ).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def chiffrer_secret(valeur: str) -> str:
    texte = (valeur or "").strip()
    if not texte:
        return ""
    if texte.startswith(PREFIX):
        return texte
    token = _fernet().encrypt(texte.encode("utf-8")).decode("ascii")
    return PREFIX + token


def dechiffrer_secret(valeur: str) -> str:
    texte = (valeur or "").strip()
    if not texte:
        return ""
    if not texte.startswith(PREFIX):
        return texte
    try:
        return _fernet().decrypt(texte[len(PREFIX) :].encode("ascii")).decode("utf-8")
    except Exception:
        logger.warning("Échec de déchiffrement d'un secret stocké.")
        return ""
