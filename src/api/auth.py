"""Authentication and authorization module for Project Valkyrie API.

Implements JWT-based authentication, API key management, and role-based access control.
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from src.database import db_manager
from sqlalchemy import Column, String, Boolean, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Security schemes
bearer_scheme = HTTPBearer()
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenData(BaseModel):
    """Token payload data."""
    sub: str  # Subject (user_id)
    exp: datetime
    iat: datetime
    type: str  # "access" or "refresh"
    roles: List[str] = []
    permissions: List[str] = []


class User(BaseModel):
    """User model for authentication."""
    id: str
    email: str
    is_active: bool = True
    is_superuser: bool = False
    roles: List[str] = []
    permissions: List[str] = []


class APIKey(BaseModel):
    """API Key model."""
    id: str
    key: str
    name: str
    user_id: str
    is_active: bool = True
    created_at: datetime
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    permissions: List[str] = []


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> TokenData:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return TokenData(**payload)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def generate_api_key() -> str:
    """Generate a secure API key."""
    return f"vk_{secrets.token_urlsafe(32)}"


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    api_key: Optional[str] = Depends(api_key_header)
) -> User:
    """Get the current authenticated user from JWT or API key."""

    # Try JWT authentication first
    if credentials:
        token_data = decode_token(credentials.credentials)

        if token_data.type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )

        # In a real implementation, fetch user from database
        # For now, return a mock user
        return User(
            id=token_data.sub,
            email=f"user_{token_data.sub}@valkyrie.com",
            roles=token_data.roles,
            permissions=token_data.permissions
        )

    # Try API key authentication
    elif api_key:
        # In a real implementation, validate API key from database
        # For now, accept any key starting with "vk_"
        if not api_key.startswith("vk_"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )

        # Return a mock user for API key auth
        return User(
            id="api_user",
            email="api@valkyrie.com",
            roles=["api_user"],
            permissions=["read", "write"]
        )

    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Ensure the current user is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


class RoleChecker:
    """Dependency for checking user roles."""

    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: User = Depends(get_current_active_user)) -> User:
        if user.is_superuser:
            return user

        if not any(role in self.allowed_roles for role in user.roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return user


class PermissionChecker:
    """Dependency for checking user permissions."""

    def __init__(self, required_permissions: List[str]):
        self.required_permissions = required_permissions

    def __call__(self, user: User = Depends(get_current_active_user)) -> User:
        if user.is_superuser:
            return user

        if not all(perm in user.permissions for perm in self.required_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return user


# Convenience functions for common role checks
def require_admin(user: User = Depends(RoleChecker(["admin"]))) -> User:
    """Require admin role."""
    return user


def require_operator(user: User = Depends(RoleChecker(["admin", "operator"]))) -> User:
    """Require operator or admin role."""
    return user


def require_viewer(user: User = Depends(RoleChecker(["admin", "operator", "viewer"]))) -> User:
    """Require viewer, operator, or admin role."""
    return user


# Permission shortcuts
def can_create_jobs(user: User = Depends(PermissionChecker(["jobs.create"]))) -> User:
    """Check permission to create jobs."""
    return user


def can_manage_companies(user: User = Depends(PermissionChecker(["companies.manage"]))) -> User:
    """Check permission to manage companies."""
    return user


def can_view_analytics(user: User = Depends(PermissionChecker(["analytics.view"]))) -> User:
    """Check permission to view analytics."""
    return user
