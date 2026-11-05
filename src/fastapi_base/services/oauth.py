from fastapi import HTTPException, status
import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models import User, UserRole
from ..schemas.auth import TokenPair
from .auth import _token_pair


async def get_or_create_oauth_user(
    db: AsyncSession,
    provider: str,
    oauth_id: str,
    email: str,
) -> User:
    # 1. Try finding by oauth provider and id
    result = await db.execute(
        select(User).filter_by(oauth_provider=provider, oauth_id=oauth_id)
    )
    user = result.scalar_one_or_none()
    if user is not None:
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user",
            )
        return user

    # 2. Try finding by email
    result = await db.execute(select(User).filter_by(email=email))
    user = result.scalar_one_or_none()
    if user is not None:
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user",
            )
        # Link existing account with OAuth
        user.oauth_provider = provider
        user.oauth_id = oauth_id
        await db.commit()
        await db.refresh(user)
        return user

    # 3. Create new user
    user_count = await db.scalar(select(func.count()).select_from(User)) or 0
    user = User(
        email=email,
        password_hash=None,
        oauth_provider=provider,
        oauth_id=oauth_id,
        role=UserRole.admin.value if user_count == 0 else UserRole.user.value,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_google(
    db: AsyncSession,
    code: str,
    redirect_uri: str,
) -> TokenPair:
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google OAuth is not configured on this server",
        )

    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient() as client:
        token_response = await client.post(token_url, data=data)
        if token_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to exchange authorization code with Google",
            )
        token_data = token_response.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google access token missing",
            )

        userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
        userinfo_response = await client.get(
            userinfo_url,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if userinfo_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to fetch user info from Google",
            )
        userinfo = userinfo_response.json()

    email = userinfo.get("email")
    oauth_id = userinfo.get("sub")
    if not email or not oauth_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incomplete user profile from Google",
        )

    user = await get_or_create_oauth_user(db, "google", str(oauth_id), email.strip().lower())
    return _token_pair(user)


async def authenticate_github(
    db: AsyncSession,
    code: str,
    redirect_uri: str,
) -> TokenPair:
    if not settings.github_client_id or not settings.github_client_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub OAuth is not configured on this server",
        )

    token_url = "https://github.com/login/oauth/access_token"
    data = {
        "client_id": settings.github_client_id,
        "client_secret": settings.github_client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
    }

    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            token_url,
            data=data,
            headers={"Accept": "application/json"},
        )
        if token_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to exchange authorization code with GitHub",
            )
        token_data = token_response.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="GitHub access token missing",
            )

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        user_response = await client.get("https://api.github.com/user", headers=headers)
        if user_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to fetch user profile from GitHub",
            )
        user_data = user_response.json()
        oauth_id = str(user_data.get("id"))
        email = user_data.get("email")

        if not email:
            # Fetch emails endpoint if email is private
            emails_response = await client.get(
                "https://api.github.com/user/emails", headers=headers
            )
            if emails_response.status_code == 200:
                emails_data = emails_response.json()
                for entry in emails_data:
                    if entry.get("primary") and entry.get("verified"):
                        email = entry.get("email")
                        break
                if not email and emails_data:
                    email = emails_data[0].get("email")

    if not email or not oauth_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incomplete user profile or missing verified email from GitHub",
        )

    user = await get_or_create_oauth_user(db, "github", oauth_id, email.strip().lower())
    return _token_pair(user)
