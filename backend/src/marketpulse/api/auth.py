import hashlib
import hmac
import time

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from marketpulse.config import Settings, get_settings

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class SessionResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def _token(settings: Settings, username: str) -> str:
    expiry = str(int(time.time()) + 3600)
    raw = f"{username}:{expiry}"
    signature = hmac.new(settings.session_secret.get_secret_value().encode(), raw.encode(), hashlib.sha256).hexdigest()
    return f"{raw}:{signature}"


def verify_session(request: Request, settings: Settings = Depends(get_settings)) -> str:  # noqa: B008
    token = request.headers.get("Authorization", "").removeprefix("Bearer ")
    parts = token.split(":")
    if len(parts) != 3:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication required")
    username, expiry, signature = parts
    raw = f"{username}:{expiry}"
    expected = hmac.new(settings.session_secret.get_secret_value().encode(), raw.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected) or int(expiry) < int(time.time()) or username != settings.admin_username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid session")
    return username


@router.post("/login", response_model=SessionResponse)
async def login(body: LoginRequest, settings: Settings = Depends(get_settings)) -> SessionResponse:  # noqa: B008
    if not hmac.compare_digest(body.username, settings.admin_username) or not hmac.compare_digest(body.password, settings.admin_password.get_secret_value()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    return SessionResponse(access_token=_token(settings, body.username))
