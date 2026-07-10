"""Google Sign-In (OAuth 2.0 / OpenID Connect), done by hand with httpx so there
are no extra dependencies.

If Google isn't configured (no client id/secret), the app runs in single-user
"local" mode: everyone is the same implicit account and no login is required —
handy for running on your own machine. Configure Google to get permanent,
account-scoped memory when deployed.
"""
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request
from starlette.responses import RedirectResponse

from . import db
from .config import settings

router = APIRouter()

_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def _redirect_uri(request: Request) -> str:
    if settings.google_redirect_uri:
        return settings.google_redirect_uri
    return str(request.url_for("auth_callback"))


def current_user(request: Request) -> dict | None:
    """The logged-in user, or the implicit local user, or None (needs login)."""
    if not settings.has_google:
        return db.get_or_create_local_user()
    uid = request.session.get("user_id")
    return db.get_user(uid) if uid else None


def require_user(request: Request) -> dict:
    user = current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="login required")
    return user


@router.get("/auth/login")
def login(request: Request):
    if not settings.has_google:
        return RedirectResponse("/")
    import secrets
    state = secrets.token_urlsafe(16)
    request.session["oauth_state"] = state
    params = urlencode({
        "client_id": settings.google_client_id,
        "redirect_uri": _redirect_uri(request),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    })
    return RedirectResponse(f"{_AUTH_URL}?{params}")


@router.get("/auth/callback", name="auth_callback")
async def callback(request: Request):
    if not settings.has_google:
        return RedirectResponse("/")
    if request.query_params.get("state") != request.session.get("oauth_state"):
        return RedirectResponse("/?auth=state_error")
    code = request.query_params.get("code")
    if not code:
        return RedirectResponse("/?auth=denied")

    async with httpx.AsyncClient(timeout=20) as client:
        tok = await client.post(_TOKEN_URL, data={
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": _redirect_uri(request),
            "grant_type": "authorization_code",
        })
        if tok.status_code != 200:
            return RedirectResponse("/?auth=token_error")
        access_token = tok.json().get("access_token")
        info = await client.get(_USERINFO_URL,
                                headers={"Authorization": f"Bearer {access_token}"})
        if info.status_code != 200:
            return RedirectResponse("/?auth=userinfo_error")
        data = info.json()

    user = db.get_or_create_google_user(
        sub=data["sub"], email=data.get("email", ""),
        name=data.get("name", ""), picture=data.get("picture", ""),
    )
    request.session.clear()
    request.session["user_id"] = user["id"]
    return RedirectResponse("/")


@router.get("/auth/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")
