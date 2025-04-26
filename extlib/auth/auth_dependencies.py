from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from .jwt_handler import verify_internal_token, credentials_exception
from .auth_models import TokenPayload, UserResponse # Use UserResponse for return type hint
from .database import get_async_session, User # Import DB session and User model
from .user_crud import get_user_by_id # Import CRUD function

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token") 

async def get_current_user_data(token: str = Depends(oauth2_scheme)) -> TokenPayload:
    """Dependency that verifies token and returns its payload."""
    return verify_internal_token(token)

async def get_current_active_user(
    token_payload: TokenPayload = Depends(get_current_user_data),
    db: AsyncSession = Depends(get_async_session)
) -> User: 
    """
    Dependency that verifies token, gets payload, and retrieves the full user object from DB.
    Raises 401 if user not found or inactive (add active check if needed).
    """
    if token_payload.sub is None:
         raise credentials_exception

    user = await get_user_by_id(db, user_id=token_payload.sub)
    if user is None:
        print(f"Authenticated user ID {token_payload.sub} not found in database.")
        raise credentials_exception
    return user

async def get_current_user_id(token_payload: TokenPayload = Depends(get_current_user_data)) -> str:
    """Dependency that verifies token and returns only the user ID."""
    if token_payload.sub is None:
         raise credentials_exception
    return token_payload.sub