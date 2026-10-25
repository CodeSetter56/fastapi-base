from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from sqlalchemy.ext.asyncio import AsyncSession

from ..cookies import REFRESH_COOKIE, clear_auth_cookies, set_auth_cookies
from ..db import get_session
from ..deps import get_current_user
from ..models import User
from ..schemas.auth import LoginRequest, RefreshRequest, TokenPair
from ..schemas.user import UserCreate, UserPublic
from ..services import auth as auth_service

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
