# extlib/auth_router.py
from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.responses import JSONResponse

from .firebase_config import verify_firebase_token
from .user_crud import get_or_create_db_user
from .jwt_handler import create_internal_access_token
from .auth_models import (
    FirebaseToken,
    InternalTokenData,
    InternalTokenResponse,
    AuthApiResponse,
    UserResponse
)
from .database import get_async_session # Import the dependency function
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.post("/google-login", response_model=AuthApiResponse, tags=["Authentication"])
async def google_login_endpoint(firebase_token_model: FirebaseToken = Body(...),
                                db: AsyncSession = Depends(get_async_session)):
    """
    Receives Firebase ID Token, verifies it, gets/creates user,
    and returns an internal JWT.
    """
    try:
        # 1. Verify Firebase ID token
        decoded_token = verify_firebase_token(firebase_token_model.token)
        print(f"Decoded token: {decoded_token}")  # Log the decoded token for debugging
        # 2. Get or create user in your database
        # Ensure the function returns a UserInDB compatible object
        app_user = await get_or_create_db_user(db,decoded_token)

        # 3. Prepare data for internal JWT payload
        internal_token_payload = InternalTokenData(
            sub=app_user.id, # Use your internal ID
            email=app_user.email,
            firebase_uid=app_user.firebase_uid
            # Add other claims if needed from app_user
        )

        # 4. Create your internal access token
        internal_access_token = create_internal_access_token(token_data=internal_token_payload)

        # 5. Prepare the response
        user_response = UserResponse.model_validate(app_user)
        token_response = InternalTokenResponse(
            token=internal_access_token,
            user=user_response
        )
        api_response = AuthApiResponse(
            data=token_response,
            status=200,
            message="Login successful"
        )
        return api_response

    except HTTPException as http_exc:
        # Re-raise known HTTP exceptions from verification
        raise http_exc
    except ValueError as ve:
         # Catch potential ValueErrors from CRUD or token data prep
         print(f"Value error during login: {ve}")
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        # Catch-all for unexpected errors during the process
        print(f"Unexpected error during Google login endpoint: {e}")
        # Consider logging the full traceback here
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during the login process."
        )
@router.post("/logout", status_code=status.HTTP_200_OK, tags=["Authentication"])
async def logout_endpoint(
):
    """
    Endpoint to handle user logout.
    This can be a no-op if you're using stateless JWTs.
    """
    # In a stateless JWT system, we might not need to do anything here.
    # Just return a success message.

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Logout successful."}
    )
# Add other endpoints later (e.g., refresh token, logout, profile)
# @router.post("/refresh-token", ...)
# async def refresh_token_endpoint(...): ...

# @router.get("/profile", ...)
# async def profile_endpoint(...): ...