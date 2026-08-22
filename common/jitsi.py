"""Utilitaires Jitsi / JaaS (8x8.vc)."""

import time
from urllib.parse import quote, urlencode

import jwt
from django.conf import settings


def _normalize_domain(domain):
    value = (domain or "").strip().rstrip("/")
    if value.startswith("https://") or value.startswith("http://"):
        value = value.split("://", 1)[1]
    return value or "meet.jit.si"


def is_jaas_enabled():
    provider = (getattr(settings, "JITSI_PROVIDER", "") or "").strip().lower()
    return provider == "jaas" or bool(getattr(settings, "JITSI_JAAS_APP_ID", ""))


def room_path(room_name):
    room_name = (room_name or "").strip()
    if is_jaas_enabled():
        app_id = (getattr(settings, "JITSI_JAAS_APP_ID", "") or "").strip().strip("/")
        if app_id:
            return f"{app_id}/{room_name}"
    return room_name


def meeting_origin():
    domain = _normalize_domain(getattr(settings, "JITSI_DOMAIN", ""))
    return f"https://{domain}"


def meeting_domain():
    return _normalize_domain(getattr(settings, "JITSI_DOMAIN", ""))


def external_api_script_url():
    domain = meeting_domain()
    app_id = (getattr(settings, "JITSI_JAAS_APP_ID", "") or "").strip().strip("/")
    if is_jaas_enabled() and app_id:
        return f"https://{domain}/{app_id}/external_api.js"
    return f"https://{domain}/external_api.js"


def build_jaas_jwt(display_name="", email="", *, is_moderator=False, user_id=""):
    app_id = (getattr(settings, "JITSI_JAAS_APP_ID", "") or "").strip()
    api_key = (getattr(settings, "JITSI_JAAS_API_KEY", "") or "").strip()
    private_key = (getattr(settings, "JITSI_JAAS_PRIVATE_KEY", "") or "").strip()
    if not (app_id and api_key and private_key):
        return ""

    now = int(time.time())
    ttl = int(getattr(settings, "JITSI_JAAS_JWT_TTL_SECONDS", 3600) or 3600)
    user_name = (display_name or "Participant").strip() or "Participant"
    user_payload = {
        "name": user_name,
        "moderator": bool(is_moderator),
    }
    if user_id:
        user_payload["id"] = str(user_id)
    if email:
        user_payload["email"] = email.strip()

    payload = {
        "aud": "jitsi",
        "iss": "chat",
        "sub": app_id,
        "room": "*",
        "nbf": now - 10,
        "exp": now + ttl,
        "context": {
            "features": {
                "livestreaming": False,
                "outbound-call": False,
                "transcription": False,
                "recording": False,
            },
            "user": user_payload,
        },
    }

    headers = {
        "kid": f"{app_id}/{api_key}",
        "typ": "JWT",
    }
    return jwt.encode(payload, private_key.replace("\\n", "\n"), algorithm="RS256", headers=headers)


def build_meeting_url(
    room_name,
    display_name="",
    email="",
    *,
    is_moderator=False,
    start_with_video_muted=False,
    user_id="",
):
    domain = _normalize_domain(getattr(settings, "JITSI_DOMAIN", ""))
    params = {
        "config.prejoinConfig.enabled": "false",
        "config.startWithAudioMuted": "false",
        "config.startWithVideoMuted": "true" if start_with_video_muted else "false",
        "config.disableDeepLinking": "true",
        "config.enableNoisyMicDetection": "true",
        "config.resolution": "720",
    }
    if display_name:
        params["userInfo.displayName"] = display_name
    if email:
        params["userInfo.email"] = email

    if is_jaas_enabled():
        token = build_jaas_jwt(
            display_name,
            email,
            is_moderator=is_moderator,
            user_id=user_id,
        )
        if token:
            # JaaS privilégie le JWT dans le fragment d'URL.
            params["jwt"] = token

    fragment = urlencode(params, quote_via=quote)
    return f"https://{domain}/{room_path(room_name)}#{fragment}"
