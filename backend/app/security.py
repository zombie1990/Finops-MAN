import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, Header, HTTPException, status

from backend.app.config import settings


@dataclass
class AuthContext:
    username: str
    tenant_id: str
    role: str
    token: str


ROLE_PERMISSIONS = {
    "FinOps Administrator": {
        "billing:read",
        "optimization:read",
        "optimization:write",
        "copilot:use",
        "connectors:read",
        "connectors:write",
        "reports:read",
        "reports:write",
    },
    "FinOps Analyst": {
        "billing:read",
        "optimization:read",
        "copilot:use",
        "connectors:read",
        "reports:read",
        "reports:write",
    },
    "Viewer": {"billing:read", "reports:read"},
}


def _urlsafe_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _urlsafe_decode(value: str) -> bytes:
    padding = "=" * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _sign(payload_part: str) -> str:
    signature = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        payload_part.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return _urlsafe_encode(signature)


def create_access_token(username: str, tenant_id: str, role: str) -> str:
    exp = int(time.time()) + (settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    payload = {"sub": username, "tenant_id": tenant_id, "role": role, "exp": exp}
    payload_part = _urlsafe_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature_part = _sign(payload_part)
    return f"{payload_part}.{signature_part}"


def decode_access_token(token: str) -> dict:
    try:
        payload_part, signature_part = token.split(".", 1)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Format de token invalide.",
        ) from exc

    expected_signature = _sign(payload_part)
    if not hmac.compare_digest(signature_part, expected_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Signature de token invalide.",
        )

    try:
        payload = json.loads(_urlsafe_decode(payload_part))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Payload de token invalide.",
        ) from exc

    if int(payload.get("exp", 0)) < int(time.time()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expiré.",
        )

    return payload


def get_auth_context(
    authorization: Optional[str] = Header(default=None),
    x_tenant_id: Optional[str] = Header(default=None),
) -> AuthContext:
    # Mode dev backward-compatible: autorise un contexte local sans token.
    if not authorization:
        if not settings.ALLOW_ANONYMOUS_AUTH:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization manquante.",
            )
        return AuthContext(
            username=settings.DEFAULT_ADMIN_USERNAME,
            tenant_id=x_tenant_id or settings.DEFAULT_TENANT_ID,
            role=settings.DEFAULT_ADMIN_ROLE,
            token="dev-anonymous-context",
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization doit utiliser le schéma Bearer.",
        )

    token = authorization.split(" ", 1)[1].strip()
    payload = decode_access_token(token)

    tenant_id = payload.get("tenant_id")
    if x_tenant_id and x_tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conflit de contexte tenant.",
        )

    return AuthContext(
        username=payload.get("sub", "unknown"),
        tenant_id=tenant_id or settings.DEFAULT_TENANT_ID,
        role=payload.get("role", "Viewer"),
        token=token,
    )


def require_permissions(*permissions: str):
    def _permission_checker(ctx: AuthContext = Depends(get_auth_context)) -> AuthContext:
        granted = ROLE_PERMISSIONS.get(ctx.role, set())
        missing = [perm for perm in permissions if perm not in granted]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permissions insuffisantes: {', '.join(missing)}",
            )
        return ctx

    return _permission_checker
