from urllib.parse import urlencode

from authlib.integrations.base_client import OAuthError
from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models import User, UserRole
from ..schemas.auth import TokenPair
from ..security import create_access_token, create_refresh_token, hash_password


oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile",
    },
)
oauth.register(
    name="github",
    client_id=settings.github_client_id,
    client_secret=settings.github_client_secret,
    access_token_url="https://github.com/login/oauth/access_token",
    authorize_url="https://github.com/login/oauth/authorize",
    api_base_url="https://api.github.com/",
    client_kwargs={"scope": "read:user user:email"},
)


def _get_oauth_client(provider: str):
    if provider not in ("google", "github"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported provider: {provider}",
        )
    return oauth.create_client(provider)  # type: ignore


async def _get_or_create_user_from_oauth(
    db: AsyncSession,
    email: str,
    provider: str,
) -> User:
    """
    Look for a user by email. If not found, create a new one.
    If found but authenticated via a different provider, we still allow login (we don't track provider).
    """
    from sqlalchemy import select

    result = await db.execute(select(User).filter_by(email=email))
    user = result.scalar_one_or_none()
    if user is None:
        # Bootstrap: if no users exist, make this user admin.
        user_count = await db.scalar(select(User)) or 0
        user = User(
            email=email,
            password_hash=hash_password("oauth2_" + urlencode({"provider": provider})),  # unusable password
            role=UserRole.admin.value if user_count == 0 else UserRole.user.value,
            is_active=True,
        )
        db.add(user)
        try:
            await db.commit()
        except Exception:
            await db.rollback()
            raise
        await db.refresh(user)
    return user


async def oauth_login(
    db: AsyncSession,
    response: Response,
    provider: str,
    code: str,
    redirect_uri: str,
) -> TokenPair:
    """
    Exchange authorization code for tokens, fetch user info, and log in (or create) the user.
    Returns a TokenPair and sets cookies.
    """
    client = _get_oauth_client(provider)
    try:
        token = await client.fetch_access_token(code, redirect_uri=redirect_uri)
    except OAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to obtain access token from {provider}: {exc.error}",
        ) from None

    # Fetch user info
    if provider == "google":
        resp = await client.get("userinfo", token=token)
        user_info = resp.json()
        email = user_info.get("email")
        # Google already verifies email, but we check anyway
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not provided by Google",
            )
    elif provider == "github":
        # GitHub requires a separate request for emails
        resp = await client.get("user", token=token)
        user_info = resp.json()
        email = user_info.get("email")
        # If email is not public, we need to fetch the emails endpoint
        if not email:
            resp2 = await client.get("user/emails", token=token)
            emails = resp2.json()
            # Find the primary email
            email_entry = next((e for e in emails if e.get("primary") and e.get("verified")), None)
            email = email_entry.get("email") if email_entry else None
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not provided by GitHub",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unsupported provider",
        )

    # Normalize email
    email = email.lower().strip()

    # Get or create user
    user = await _get_or_create_user_from_oauth(db, email, provider)

    # Generate our JWT pair
    pair = TokenPair(
        access_token=create_access_token(user.id, user.token_version),
        refresh_token=create_refresh_token(user.id, user.token_version),
    )
    # Set cookies (same as regular login)
    from ..cookies import set_auth_cookies

    set_auth_cookies(response, pair)
    return pair