import os

import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv
from contextlib import asynccontextmanager # Import for lifespan
load_dotenv()
#from google.adk.cli.fast_api import get_fast_api_app
from extlib.custom_fast_api import get_my_fast_api_app
#---- add auth stuff here ----
from extlib.auth.firebase_config import initialize_firebase
from extlib.auth.database import create_db_and_tables
from extlib.auth.auth_router import router as auth_router



# Get the directory where main.py is located
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
# Example session DB URL (e.g., SQLite)
SESSION_DB_URL = "sqlite:///./sessions.db"
# Example allowed origins for CORS
ALLOWED_ORIGINS = ("*",)
# Set web=True if you intend to serve a web interface, False otherwise
SERVE_WEB_INTERFACE = False

# --- Lifespan Context Manager ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code to run on startup
    print("Application startup...")
    initialize_firebase()       # Initialize Firebase Admin
    await create_db_and_tables() # Create database tables
    print("Startup complete.")
    yield
    # Code to run on shutdown
    print("Application shutdown...")
    # Add cleanup code here if needed (e.g., close DB engine gracefully?)
    # await engine.dispose() # Example if using SQLAlchemy engine directly
    print("Shutdown complete.")

app: FastAPI = get_my_fast_api_app(
    agent_dir=AGENT_DIR,
    session_db_url=SESSION_DB_URL,
    allow_origins=ALLOWED_ORIGINS,
    web=SERVE_WEB_INTERFACE,
    lifespan=lifespan,  # Use the lifespan context manager
)
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
@app.get("/")
async def root():
    return {"message": "Welcome - API Root"}

if __name__ == "__main__":
    # Use the PORT environment variable provided by Cloud Run, defaulting to 8080
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
