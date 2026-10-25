from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from typing import Literal, cast

from sqlalchemy.ext.asyncio import AsyncSession

from ..cookies import REFRESH_COOKIE, clear_auth_cookies, set_auth_cookies
from ..config import settings
from ..db import get_session
from ..deps import get_current_user
from ..models import User
from ..schemas.auth import LoginRequest, RefreshRequest, TokenPair
from ..schemas.user import UserCreate, UserPublic
from ..services import auth as auth_service, oauth2 as oauth2_service

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


@router.get("/oauth2/{provider}")
async def oauth2_authorize(
    provider: str,
    request: Request,
    response: Response,
):
    """
    Redirect to the OAuth2 provider for authentication.
    """
    # For simplicity, we use a fixed redirect URI; in production, you might want to make this configurable.
    # We'll use the same host as the request, but you can also set it via environment variable.
    redirect_uri = str(request.base_url) + f"auth/oauth2/{provider}/callback"
    client = oauth2_service._get_oauth_client(provider)
    # Generate a random state token to prevent CSRF
    import secrets
    state = secrets.token_urlsafe(32)
    # Store state in cookie for verification in callback
    response.set_cookie(
        key=f"oauth_state_{provider}",
        value=state,
        httponly=True,
        secure=settings.cookie_secure,  # Use same setting as auth cookies
        samesite=cast(Literal["lax", "strict", "none"] | None, settings.cookie_samesite),
        max_age=600,  # 10 minutes
    )
    # Create authorization URL with state
    authorization_url = client.create_authorization_url(
        redirect_uri,
        state=state,
        prompt="consent"
    )[0]
    return RedirectResponse(authorization_url)


@router.get("/oauth2/{provider}/callback")
async def oauth2_callback(
    provider: str,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_session),
):
    """
    Handle the callback from the OAuth2 provider.
    """
    # Extract the authorization code and state from the query parameters
    code = request.query_params.get("code")
    state = request.query_params.get("state")

    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing code parameter",
        )

    # Verify state parameter to prevent CSRF
    expected_state = request.cookies.get(f"oauth_state_{provider}")
    if not expected_state or state != expected_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter",
        )

    # Use the same redirect URI as in the authorize step
    redirect_uri = str(request.base_url) + f"auth/oauth2/{provider}/callback"
    try:
        pair = await oauth2_service.oauth_login(
            db, response, provider, code, redirect_uri
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth2 login failed: {exc}",
        ) from exc

    # Clear the state cookie
    response.delete_cookie(key=f"oauth_state_{provider}")

    # Return a JSON response with the token pair (optional; you could also redirect to a frontend)
    return {"access_token": pair.access_token, "refresh_token": pair.refresh_token, "token_type": "bearer"}
