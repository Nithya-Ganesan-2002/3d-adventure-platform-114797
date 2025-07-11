from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import engine
from .models import Base

app = FastAPI()

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

@app.get("/")
def health_check():
    """Health check for game backend."""
    return {"message": "Healthy"}
