from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import (
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthTokenResponse,
    UserPublic,
)
from src.auth.deps import get_current_user, get_db_session
from src.auth.security import create_access_token, hash_password, verify_password
from src.db.models import AppUser

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=AuthTokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Creates a new account and returns a JWT access token.",
    operation_id="auth_register",
)
async def register(payload: AuthRegisterRequest, session: AsyncSession = Depends(get_db_session)) -> AuthTokenResponse:
    """Register a new user and return access token."""
    existing = await session.execute(select(AppUser).where(AppUser.email == payload.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = AppUser(
        email=payload.email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
    )
    session.add(user)
    await session.flush()  # get id

    token = create_access_token(str(user.id))
    return AuthTokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserPublic(id=user.id, email=user.email, display_name=user.display_name),
    )


@router.post(
    "/login",
    response_model=AuthTokenResponse,
    summary="Login",
    description="Validates credentials and returns a JWT access token.",
    operation_id="auth_login",
)
async def login(payload: AuthLoginRequest, session: AsyncSession = Depends(get_db_session)) -> AuthTokenResponse:
    """Login existing user and return access token."""
    result = await session.execute(select(AppUser).where(AppUser.email == payload.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(str(user.id))
    return AuthTokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserPublic(id=user.id, email=user.email, display_name=user.display_name),
    )


@router.get(
    "/me",
    response_model=UserPublic,
    summary="Get current user",
    description="Returns the currently authenticated user.",
    operation_id="auth_me",
)
async def me(user: AppUser = Depends(get_current_user)) -> UserPublic:
    """Return current authenticated user."""
    return UserPublic(id=user.id, email=user.email, display_name=user.display_name)
