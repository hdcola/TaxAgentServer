import os
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from .auth_models import InternalTokenData, TokenPayload

JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
print("get:",JWT_SECRET_KEY)
if JWT_SECRET_KEY == "your-secret-key":
     print("WARNING: Using default JWT_SECRET_KEY. Please set a strong secret in your environment variables.")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24))

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)
expired_token_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Token has expired",
    headers={"WWW-Authenticate": "Bearer"},
)

def create_internal_access_token(token_data: InternalTokenData) -> str:
    """Creates an internal JWT access token."""
    to_encode = token_data.model_dump(exclude_unset=True)
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def verify_internal_token(token: str) -> TokenPayload:
    """Verifies the internal JWT and returns the payload."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        token_data = TokenPayload(**payload)
        if token_data.sub is None:
             print("Token verification failed: 'sub' claim missing")
             raise credentials_exception
        return token_data
    except jwt.ExpiredSignatureError:
        print("Token verification failed: Expired")
        raise expired_token_exception
    except jwt.InvalidTokenError as e:
        print(f"Token verification failed: Invalid token - {e}")
        raise credentials_exception
    except Exception as e: # Catch potential Pydantic validation errors or others
         print(f"Token verification failed: Unexpected error - {e}")
         raise credentials_exception