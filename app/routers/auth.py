from fastapi import APIRouter, Depends, Body, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.models.user import UserCreate, UserResponse
from app.models.token import Token
from app.services.auth import auth_service
from app.services.firestore import firestore_service
from app.core.security import get_password_hash

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate = Body(...)):
    """
    Register a new user.
    
    Args:
        user: User registration data
        
    Returns:
        Created user data
    """
    # Check if user with this email already exists
    existing_user = await firestore_service.get_user_by_email(user.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Hash the password
    hashed_password = get_password_hash(user.password)
    
    # Prepare user data
    user_data = user.dict()
    user_data.pop("password")
    user_data["hashed_password"] = hashed_password
    
    # Create user
    created_user = await firestore_service.create_user(user_data)
    return created_user

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Login and get access token.
    
    Args:
        form_data: OAuth2 password request form
        
    Returns:
        Access token
    """
    user = await auth_service.authenticate_user(form_data.username, form_data.password)
    access_token = auth_service.create_access_token(user["id"])
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def get_current_user(current_user: dict = Depends(auth_service.get_current_user)):
    """
    Get current authenticated user.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User data
    """
    return current_user