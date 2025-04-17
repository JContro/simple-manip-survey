from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from jose import jwt, JWTError
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings
from app.core.security import verify_password, get_password_hash
from app.core.exceptions import AuthenticationError
from app.models.token import TokenPayload
from app.services.firestore import firestore_service

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

class AuthService:
    """
    Service for authentication and authorization.
    """
    
    async def authenticate_user(self, email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate a user with email and password.
        
        Args:
            email: User email
            password: User password
            
        Returns:
            User data if authentication successful
            
        Raises:
            AuthenticationError: If authentication fails
        """
        user = await firestore_service.get_user_by_email(email)
        if not user:
            raise AuthenticationError("Incorrect email or password")
        
        if not verify_password(password, user["hashed_password"]):
            raise AuthenticationError("Incorrect email or password")
        
        return user
    
    def create_access_token(self, user_id: str) -> str:
        """
        Create an access token for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            JWT access token
        """
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        expire = datetime.utcnow() + expires_delta
        
        to_encode = {"sub": user_id, "exp": expire}
        encoded_jwt = jwt.encode(
            to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
        )
        return encoded_jwt
    
    async def get_current_user(self, token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
        """
        Get the current authenticated user from a JWT token.
        
        Args:
            token: JWT token
            
        Returns:
            User data
            
        Raises:
            AuthenticationError: If token is invalid or user not found
        """
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            token_data = TokenPayload(**payload)
            
            if token_data.sub is None:
                raise AuthenticationError("Invalid token")
            
            user = await firestore_service.get_user_by_id(token_data.sub)
            if user is None:
                raise AuthenticationError("User not found")
            
            return user
        except JWTError:
            raise AuthenticationError("Invalid token")

# Create a singleton instance
auth_service = AuthService()