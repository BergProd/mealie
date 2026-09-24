"""Exchange Zpace's unsigned identity cookie for a Mealie session JWT.

Zpace v1 identity is an unsigned JWT in the ``zpace_access`` cookie. The edge
decodes the payload only (no signature check). Mealie does the same, then maps
the identity onto a Mealie user and mints a normal Mealie access token.
"""

from __future__ import annotations

import base64
import json
import re
from datetime import timedelta
from logging import Logger

from sqlalchemy import func, select
from sqlalchemy.orm.session import Session

from mealie.core import root_logger
from mealie.core.config import get_app_settings
from mealie.core.security.tokens import create_access_token
from mealie.db.models.users.users import AuthMethod, User
from mealie.repos.all_repositories import get_repositories
from mealie.schema.user import PrivateUser

ZPACE_COOKIE_NAME = "zpace_access"
_SYNTHETIC_EMAIL_DOMAIN = "users.zpace.se"
_USERNAME_SAFE = re.compile(r"[^a-zA-Z0-9._-]+")

logger: Logger = root_logger.get_logger("zpace_access")


def decode_zpace_access_payload(token: str) -> dict | None:
    """Decode the JWT payload without verifying a signature (matches Zpace edge)."""
    if not token or not token.strip():
        return None

    parts = token.strip().split(".")
    if len(parts) < 2:
        return None

    try:
        padded = parts[1] + "=" * (-len(parts[1]) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
        payload = json.loads(raw.decode("utf-8"))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None

    return payload if isinstance(payload, dict) else None


def identity_from_zpace_payload(payload: dict) -> tuple[str, str] | None:
    """Return ``(sub, email)`` from a Zpace payload, or None if ``sub`` is missing."""
    sub = payload.get("sub")
    if not isinstance(sub, str) or not sub.strip():
        return None

    sub = sub.strip()
    email_claim = payload.get("email")
    if isinstance(email_claim, str) and email_claim.strip():
        email = email_claim.strip().lower()
    else:
        email = f"{sub}@{_SYNTHETIC_EMAIL_DOMAIN}".lower()

    return sub, email


def _username_for(sub: str, email: str) -> str:
    local = email.split("@", 1)[0]
    candidate = _USERNAME_SAFE.sub("-", local).strip(".-_") or _USERNAME_SAFE.sub("-", sub)
    return (candidate or "zpace-user")[:50]


def _find_user_row(session: Session, sub: str, email: str) -> User | None:
    by_sub = session.execute(select(User).where(User.zpace_sub == sub)).scalar_one_or_none()
    if by_sub:
        return by_sub
    return session.execute(select(User).where(func.lower(User.email) == email.lower())).scalar_one_or_none()


def ensure_mealie_user(
    session: Session,
    sub: str,
    email: str,
    full_name: str | None,
    *,
    admin: bool | None = None,
) -> PrivateUser | None:
    """Look up by LinkSubject, then email. Create into the existing default group when missing."""
    settings = get_app_settings()
    repos = get_repositories(session, group_id=None, household_id=None)

    existing = _find_user_row(session, sub, email)
    if existing:
        changed = False
        if not existing.zpace_sub:
            existing.zpace_sub = sub
            changed = True
        if admin is not None and existing.admin != admin:
            existing.admin = admin
            changed = True
        if changed:
            session.commit()
        return repos.users.get_one(existing.id)

    username = _username_for(sub, email)
    if repos.users.get_by_username(username):
        username = f"{username[:40]}-{sub[:8]}"

    display_name = full_name.strip() if isinstance(full_name, str) and full_name.strip() else email

    try:
        # User model resolves DEFAULT_GROUP / DEFAULT_HOUSEHOLD (Home / Family) when omitted.
        user = repos.users.create(
            {
                "username": username,
                "password": "ZPACE",
                "full_name": display_name,
                "email": email,
                "admin": bool(admin),
                "auth_method": AuthMethod.OIDC,
                "group": settings.DEFAULT_GROUP,
                "household": settings.DEFAULT_HOUSEHOLD,
            }
        )
        created = session.get(User, user.id)
        if created is not None:
            created.zpace_sub = sub
        session.commit()
        logger.info("Created Mealie user for Zpace subject %s (%s)", sub, email)
        return user
    except Exception:
        logger.exception("Failed to create Mealie user for Zpace subject %s", sub)
        session.rollback()
        return None


def exchange_zpace_access_for_mealie_token(
    session: Session,
    token: str,
    *,
    remember_me: bool = True,
) -> tuple[str, timedelta] | None:
    """Resolve ``zpace_access`` to a Mealie JWT, creating the user when needed."""
    payload = decode_zpace_access_payload(token)
    if not payload:
        return None

    identity = identity_from_zpace_payload(payload)
    if not identity:
        return None

    sub, email = identity
    name = payload.get("name") or payload.get("preferred_username")
    user = ensure_mealie_user(session, sub, email, name if isinstance(name, str) else None)
    if not user:
        return None

    return create_access_token({"sub": str(user.id), "rme": remember_me})