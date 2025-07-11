"""
Handles user registration, login, and JWT authentication for the 3D adventure game backend.
"""

import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.orm import Session
from passlib.context import CryptContext
import jwt

from .db import get_db
from .models import User

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "SUPER_SECRET_DEVELOPMENT_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

# Pydantic schemas
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=32, description="Unique username")
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

# Utility functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(user_id: int, username: str, expires_delta: Optional[timedelta] = None):
    to_encode = {
        "sub": str(user_id),
        "username": username,
        "exp": datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)),
    }
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        username = payload.get("username")
        return {"user_id": user_id, "username": username}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except (jwt.PyJWTError, Exception):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate token")

# PUBLIC_INTERFACE
@auth_router.post("/register", response_model=Token, summary="User registration", description="Register a new user, returns JWT upon success")
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user. Returns JWT access token if successful.

    - **username**: Unique username (3-32 characters)
    - **email**: Unique email
    - **password**: Password (at least 6 chars)
    """
    existing_user = db.query(User).filter((User.username == user.username) | (User.email == user.email)).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username or email already registered"
        )
    user_obj = User(
        username=user.username,
        email=user.email,
        password_hash=get_password_hash(user.password)
    )
    db.add(user_obj)
    db.commit()
    db.refresh(user_obj)
    access_token = create_access_token(user_id=user_obj.id, username=user_obj.username)
    return {"access_token": access_token, "token_type": "bearer"}

# PUBLIC_INTERFACE
@auth_router.post("/login", response_model=Token, summary="User login", description="Authenticate user and return JWT")
def login_user(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    User login. Returns JWT access token if authentication is successful.

    - **username**: Username (NOT email)
    - **password**: Password
    """
    user = db.query(User).filter(User.username == form.username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect credentials")
    if not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect credentials")
    access_token = create_access_token(user_id=user.id, username=user.username)
    return {"access_token": access_token, "token_type": "bearer"}

# PUBLIC_INTERFACE
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """
    Dependency that extracts and returns the current authenticated user object.
    Raises 401 if the token is invalid/expired.
    """
    token_data = decode_access_token(token)
    user = db.query(User).filter(User.id == token_data["user_id"]).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user
