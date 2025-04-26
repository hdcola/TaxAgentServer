import os
from datetime import datetime, timedelta
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from google.adk.cli.fast_api import get_fast_api_app
import jwt
from jwt.exceptions import InvalidTokenError
from dotenv import load_dotenv
load_dotenv()

# Get the directory where main.py is located
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
# Example session DB URL (e.g., SQLite)
SESSION_DB_URL = "sqlite:///./sessions.db"
# Example allowed origins for CORS
ALLOWED_ORIGINS = ("*",)
# Set web=True if you intend to serve a web interface, False otherwise
SERVE_WEB_INTERFACE = False

# JWT Configuration
JWT_SECRET_KEY = os.environ.get(
    "JWT_SECRET_KEY", "your-secret-key")  # Change in production
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 30  # Token expiration time in minutes

# Call the function to get the FastAPI app instance
app: FastAPI = get_fast_api_app(
    agent_dir=AGENT_DIR,
    session_db_url=SESSION_DB_URL,
    allow_origins=ALLOWED_ORIGINS,
    web=SERVE_WEB_INTERFACE,
)


@app.middleware("http")
async def jwt_middleware(request, call_next):
    """
    Middleware to handle JWT authentication
    """
    # Skip JWT verification for specific paths (like login endpoints)
    excluded_paths = ["/list-apps"]
    if any(request.url.path.startswith(path) for path in excluded_paths):
        return await call_next(request)

    # Handle OPTIONS requests properly - allow them through without token check
    # but ensure other request types are still authenticated
    if request.method == "OPTIONS":
        response = await call_next(request)
        return response

    # Extract token from Authorization header
    authorization = request.headers.get("Authorization")
    if not authorization:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Authorization header missing"}
        )

    try:
        token_type, token = authorization.split()
        if token_type.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid token type")

        # Verify the JWT token
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY,
                                 algorithms=[JWT_ALGORITHM])
            # You can extract user information from payload if needed
            # user_id = payload.get("sub")
            # request.state.user = user_id  # Store user info in request state
        except InvalidTokenError:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or expired token"}
            )

    except Exception:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Invalid authentication credentials"}
        )

    # Proceed with the request if token is valid
    response = await call_next(request)
    return response


# Example login endpoint (uncomment and customize as needed)
# @app.post("/login")
# async def login(username: str, password: str):
#     # Validate user credentials here
#     # ...
#     access_token = create_access_token(data={"sub": username})
#     return {"access_token": access_token, "token_type": "bearer"}


if __name__ == "__main__":
    # Use the PORT environment variable provided by Cloud Run, defaulting to 8080
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
