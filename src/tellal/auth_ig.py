"""Instagram Login (OAuth) for a Meta app you own.

Flow: the owner opens authorize_url() -> Instagram asks them to allow access -> Instagram redirects back
to {public_url}/auth/instagram/callback?code=... -> we swap the code for a short-lived token, then for a
60-day token, which the scheduler refreshes before it runs out.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from urllib.parse import urlencode

import httpx

SCOPES = [
    "instagram_business_basic",
    "instagram_business_content_publish",
    "instagram_business_manage_comments",
    "instagram_business_manage_insights",
]


def redirect_uri(settings) -> str:  # noqa: ANN001
    return f"{settings.public_url}/auth/instagram/callback"


def make_state(secret: str) -> str:
    nonce = secrets.token_urlsafe(12)
    ts = str(int(time.time()))
    sig = hmac.new(secret.encode(), f"{nonce}.{ts}".encode(), hashlib.sha256).hexdigest()[:24]
    return f"{nonce}.{ts}.{sig}"


def check_state(secret: str, state: str, max_age: int = 900) -> bool:
    try:
        nonce, ts, sig = state.split(".")
    except ValueError:
        return False
    good = hmac.new(secret.encode(), f"{nonce}.{ts}".encode(), hashlib.sha256).hexdigest()[:24]
    return hmac.compare_digest(good, sig) and time.time() - int(ts) < max_age


def authorize_url(settings, state: str) -> str:  # noqa: ANN001
    q = {
        "client_id": settings.ig_app_id,
        "redirect_uri": redirect_uri(settings),
        "response_type": "code",
        "scope": ",".join(SCOPES),
        "state": state,
        "enable_fb_login": "0",
        "force_reauth": "true",
    }
    return "https://www.instagram.com/oauth/authorize?" + urlencode(q)


def exchange_code(settings, code: str, transport: httpx.BaseTransport | None = None) -> tuple[str, str, float]:  # noqa: ANN001
    """Returns (user_id, long_lived_token, expires_at)."""
    with httpx.Client(timeout=30, transport=transport) as c:
        r = c.post(
            "https://api.instagram.com/oauth/access_token",
            data={
                "client_id": settings.ig_app_id,
                "client_secret": settings.ig_app_secret,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri(settings),
                "code": code.removesuffix("#_"),
            },
        )
        b = r.json()
        if r.status_code >= 400 or "access_token" not in b:
            raise ValueError(b.get("error_message") or b.get("error", {}).get("message") or "token exchange failed")
        short, user_id = b["access_token"], str(b.get("user_id"))
        r = c.get(
            "https://graph.instagram.com/access_token",
            params={"grant_type": "ig_exchange_token", "client_secret": settings.ig_app_secret, "access_token": short},
        )
        b = r.json()
        if r.status_code >= 400 or "access_token" not in b:
            raise ValueError(b.get("error", {}).get("message") or "long-lived token exchange failed")
        return user_id, b["access_token"], time.time() + float(b.get("expires_in") or 5_184_000)
