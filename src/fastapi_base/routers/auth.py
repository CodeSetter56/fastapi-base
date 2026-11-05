from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..token.cookies import REFRESH_COOKIE, clear_auth_cookies, set_auth_cookies
from ..db import get_session
from ..deps import get_current_user
from ..models import User
from ..schemas.auth import LoginRequest, RefreshRequest, TokenPair
from ..schemas.user import UserCreate, UserPublic
from ..services import auth as auth_service
from ..services import oauth as oauth_service

router = APIRouter()


@router.post(
    "/register",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    req: UserCreate,
    db: AsyncSession = Depends(get_session),
) -> User:
    return await auth_service.register(db, req)


@router.post("/login", response_model=TokenPair)
async def login(
    req: LoginRequest,
    res: Response,
    db: AsyncSession = Depends(get_session),
) -> TokenPair:
    pair = await auth_service.login(db, req)
    set_auth_cookies(res, pair)
    return pair


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    request: Request,
    response: Response,
    req: RefreshRequest | None = None,
    db: AsyncSession = Depends(get_session),
) -> TokenPair:
    refresh_token = (
        req.refresh_token if req is not None else None
    ) or request.cookies.get(REFRESH_COOKIE)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    pair = await auth_service.refresh(db, refresh_token)
    set_auth_cookies(response, pair)
    return pair


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> None:
    await auth_service.logout(db, current_user)
    clear_auth_cookies(response)


@router.get("/google/login", include_in_schema=True)
async def google_login(request: Request) -> RedirectResponse:
    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google OAuth is not configured",
        )
    redirect_uri = str(request.url_for("google_callback"))
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={settings.google_client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope=openid%20email%20profile"
    )
    return RedirectResponse(url=auth_url, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/google/callback", name="google_callback")
async def google_callback(
    request: Request,
    response: Response,
    code: str,
    db: AsyncSession = Depends(get_session),
) -> RedirectResponse:
    redirect_uri = str(request.url_for("google_callback"))
    pair = await oauth_service.authenticate_google(db, code, redirect_uri)
    set_auth_cookies(response, pair)
    return RedirectResponse(url=settings.frontend_url, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/github/login", include_in_schema=True)
async def github_login(request: Request) -> RedirectResponse:
    if not settings.github_client_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub OAuth is not configured",
        )
    redirect_uri = str(request.url_for("github_callback"))
    auth_url = (
        f"https://github.com/login/oauth/authorize?"
        f"client_id={settings.github_client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"scope=user:email"
    )
    return RedirectResponse(url=auth_url, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/github/callback", name="github_callback")
async def github_callback(
    request: Request,
    response: Response,
    code: str,
    db: AsyncSession = Depends(get_session),
) -> RedirectResponse:
    redirect_uri = str(request.url_for("github_callback"))
    pair = await oauth_service.authenticate_github(db, code, redirect_uri)
    set_auth_cookies(response, pair)
    return RedirectResponse(url=settings.frontend_url, status_code=status.HTTP_303_SEE_OTHER)
