from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from .db import engine
from .models import Base
from .auth import auth_router, get_current_user
from .game import game_router

app = FastAPI(
    title="3D Adventure Game Backend",
    description="Handles game logic, user authentication, leaderboard, progress, inventory, and more for the 3D adventure platform.",
    version="0.1.0",
    openapi_tags=[
        {"name": "Authentication", "description": "Endpoints related to user registration, login and tokens."},
        {"name": "Game Actions", "description": "Endpoints for world movement, interaction, inventory, progress, and leaderboard"},
        {"name": "Misc", "description": "Miscellaneous endpoints."}
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    """
    FastAPI startup event: ensure all database tables are created.
    """
    Base.metadata.create_all(bind=engine)

app.include_router(auth_router)
app.include_router(game_router)

@app.get("/", tags=["Misc"])
def health_check():
    """Health check for game backend."""
    return {"message": "Healthy"}

# PUBLIC_INTERFACE
@app.get("/protected", summary="Example of protected route", tags=["Authentication"])
def protected(test_user=Depends(get_current_user)):
    """
    Example endpoint that is only accessible to authenticated users (JWT required).

    Returns the user's username and ID.
    """
    return {"user_id": test_user.id, "username": test_user.username}
