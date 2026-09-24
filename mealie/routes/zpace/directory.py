import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm.session import Session

from mealie.core.config import get_app_settings
from mealie.core.security.zpace_access import ensure_mealie_user, identity_from_zpace_payload
from mealie.db.db_setup import generate_session

router = APIRouter(prefix="/zpace", tags=["Zpace"])

DIRECTORY_SECRET_HEADER = "X-Zpace-Directory-Secret"


class DirectoryUserIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    link_subject: str = Field(alias="linkSubject")
    email: str | None = None
    name: str | None = None
    admin: bool = False
    apply_baseline: bool = Field(default=False, alias="applyBaseline")


class DirectoryUserOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True, ser_json_by_alias=True)

    app_user_id: str = Field(serialization_alias="appUserId")
    admin: bool


def _require_secret(supplied: str | None) -> None:
    expected = (get_app_settings().ZPACE_DIRECTORY_SECRET or "").strip()
    if not expected:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Zpace directory secret is not configured")
    if not supplied or not secrets.compare_digest(supplied.strip(), expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid directory secret")


def apply_baseline() -> None:
    settings = get_app_settings()
    settings.ALLOW_SIGNUP = False
    settings.ALLOW_PASSWORD_LOGIN = False


@router.post("/directory", response_model=DirectoryUserOut, response_model_by_alias=True)
def upsert_directory_user(
    body: DirectoryUserIn,
    session: Session = Depends(generate_session),
    directory_secret: str | None = Header(default=None, alias=DIRECTORY_SECRET_HEADER),
) -> DirectoryUserOut:
    _require_secret(directory_secret)
    identity = identity_from_zpace_payload({"sub": body.link_subject, "email": body.email, "name": body.name})
    if not identity:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="linkSubject is required")

    sub, email = identity
    if body.apply_baseline:
        apply_baseline()

    user = ensure_mealie_user(session, sub, email, body.name, admin=body.admin)
    if user is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Could not ensure Mealie user")

    return DirectoryUserOut(app_user_id=str(user.id), admin=bool(user.admin))
