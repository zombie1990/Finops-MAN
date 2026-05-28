import secrets
from typing import Dict, Optional
from urllib.parse import urlencode

import httpx

from backend.app.config import settings
from backend.app.security import create_access_token

_oidc_state_store: Dict[str, str] = {}


class OidcService:
    @staticmethod
    def is_enabled() -> bool:
        return (
            settings.OIDC_ENABLED
            and settings.OIDC_ISSUER
            and settings.OIDC_CLIENT_ID
            and settings.OIDC_CLIENT_SECRET
        )

    @staticmethod
    def _issuer_base() -> str:
        return settings.OIDC_ISSUER.rstrip("/")

    @staticmethod
    def get_authorization_url() -> Dict[str, str]:
        if not OidcService.is_enabled():
            raise ValueError("OIDC non configuré.")
        state = secrets.token_urlsafe(24)
        _oidc_state_store[state] = settings.DEFAULT_TENANT_ID
        params = {
            "client_id": settings.OIDC_CLIENT_ID,
            "response_type": "code",
            "scope": settings.OIDC_SCOPES,
            "redirect_uri": settings.OIDC_REDIRECT_URI,
            "state": state,
        }
        url = f"{OidcService._issuer_base()}/oauth2/v2.0/authorize?{urlencode(params)}"
        return {"authorization_url": url, "state": state}

    @staticmethod
    def exchange_code(code: str, state: str) -> Dict[str, str]:
        if state not in _oidc_state_store:
            raise ValueError("State OIDC invalide.")
        tenant_id = _oidc_state_store.pop(state)

        token_url = f"{OidcService._issuer_base()}/oauth2/v2.0/token"
        data = {
            "grant_type": "authorization_code",
            "client_id": settings.OIDC_CLIENT_ID,
            "client_secret": settings.OIDC_CLIENT_SECRET,
            "code": code,
            "redirect_uri": settings.OIDC_REDIRECT_URI,
            "scope": settings.OIDC_SCOPES,
        }
        with httpx.Client(timeout=20.0) as client:
            token_res = client.post(token_url, data=data)
            token_res.raise_for_status()
            tokens = token_res.json()

            userinfo_res = client.get(
                f"{OidcService._issuer_base()}/oidc/userinfo",
                headers={"Authorization": f"Bearer {tokens['access_token']}"},
            )
            userinfo = userinfo_res.json() if userinfo_res.status_code == 200 else {}

        username = userinfo.get("preferred_username") or userinfo.get("email") or "oidc_user"
        role = settings.DEFAULT_ADMIN_ROLE
        app_token = create_access_token(username=username, tenant_id=tenant_id, role=role)
        return {
            "username": username,
            "tenant_id": tenant_id,
            "role": role,
            "token": app_token,
        }
