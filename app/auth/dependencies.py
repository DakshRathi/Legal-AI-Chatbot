# app/auth/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select # Import select for queries

from app.db.database import get_db
from app.db.models import User
from app.auth.security import decode_access_token
from app.models.token import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token") # Points to your login endpoint

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to get the current user from the JWT token.
    Raises HTTPException if token is invalid or user not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    username: str = payload.get("sub") # Assuming subject ('sub') is username
    user_id: int = payload.get("user_id") # Get user_id from payload
    if username is None or user_id is None:
        raise credentials_exception

    token_data = TokenData(username=username, user_id=user_id)

    # Fetch user from DB using user_id for better performance/reliability
    query = select(User).where(User.id == token_data.user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Optional dependency: Check if the user is active (if you add an is_active flag).
    For now, it just returns the user retrieved by get_current_user.
    """
    # if not current_user.is_active: # Example if you add an is_active field
    #     raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
