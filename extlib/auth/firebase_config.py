import os
import firebase_admin
from firebase_admin import credentials, auth
from fastapi import HTTPException, status

is_firebase_initialized = False

def initialize_firebase():
    """Initializes the Firebase Admin SDK using credentials from env variable."""
    global is_firebase_initialized
    if is_firebase_initialized:
        print("Firebase Admin SDK already initialized.")
        return

    SERVICE_ACCOUNT_KEY_PATH = os.environ.get("FIREBASE_SERVICE_ACCOUNT_KEY_PATH")
    if not SERVICE_ACCOUNT_KEY_PATH:
        print("WARNING: FIREBASE_SERVICE_ACCOUNT_KEY_PATH environment variable not set. Firebase Admin SDK not initialized.")
        # Decide how critical this is. Maybe raise an error or log prominently.
        # raise ValueError("FIREBASE_SERVICE_ACCOUNT_KEY_PATH environment variable not set.")
        return # Exit if path not set

    if not os.path.exists(SERVICE_ACCOUNT_KEY_PATH):
        print(f"WARNING: Service account key not found at: {SERVICE_ACCOUNT_KEY_PATH}. Firebase Admin SDK not initialized.")
        # raise FileNotFoundError(f"Service account key not found at: {SERVICE_ACCOUNT_KEY_PATH}")
        return # Exit if file not found

    try:
        cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
        firebase_admin.initialize_app(cred)
        is_firebase_initialized = True
        print("Firebase Admin SDK initialized successfully.")
    except Exception as e:
        is_firebase_initialized = False
        print(f"CRITICAL ERROR: Failed to initialize Firebase Admin SDK: {e}")
        # Depending on your app's needs, you might want to raise this exception
        # raise RuntimeError(f"Could not initialize Firebase Admin SDK: {e}") from e

def verify_firebase_token(id_token: str) -> dict:
    """Verifies the Firebase ID token and returns the decoded claims."""
    if not is_firebase_initialized:
         raise HTTPException(
             status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
             detail="Firebase Admin SDK is not initialized. Cannot verify token."
         )
    try:
        decoded_token = auth.verify_id_token(id_token)
        print(f"Decoded Firebase token: {decoded_token}") # Log the decoded token
        return decoded_token
    except auth.ExpiredIdTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Firebase token has expired")
    except auth.InvalidIdTokenError as e:
        print(f"Invalid Firebase token error: {e}") # Log detailed error
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid Firebase token: {e}")
    except Exception as e:
        print(f"Unexpected error verifying Firebase token: {e}") # Log unexpected errors
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not verify Firebase token due to an internal error.")
