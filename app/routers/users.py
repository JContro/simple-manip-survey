from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Path, Body, HTTPException, status

from app.models.user import UserCreate, UserUpdate, UserResponse
from app.services.firestore import firestore_service
from app.services.auth import auth_service
from app.core.security import get_password_hash

router = APIRouter()

@router.get("/", response_model=List[UserResponse])
async def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: dict = Depends(auth_service.get_current_user)
):
    """
    Get a list of users.
    
    Args:
        skip: Number of users to skip
        limit: Maximum number of users to return
        current_user: Current authenticated user
        
    Returns:
        List of users
    """
    users = await firestore_service.get_users(limit=limit, offset=skip)
    return users

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str = Path(...),
    current_user: dict = Depends(auth_service.get_current_user)
):
    """
    Get a specific user by ID.
    
    Args:
        user_id: User ID
        current_user: Current authenticated user
        
    Returns:
        User data
    """
    user = await firestore_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    return user

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate = Body(...)):
    """
    Create a new user.
    
    Args:
        user: User data
        
    Returns:
        Created user data
    """
    # Hash the password
    hashed_password = get_password_hash(user.password)
    
    # Prepare user data
    user_data = user.dict()
    user_data.pop("password")
    user_data["hashed_password"] = hashed_password
    
    # Create user
    created_user = await firestore_service.create_user(user_data)
    return created_user

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str = Path(...),
    user: UserUpdate = Body(...),
    current_user: dict = Depends(auth_service.get_current_user)
):
    """
    Update a user.
    
    Args:
        user_id: User ID
        user: User data to update
        current_user: Current authenticated user
        
    Returns:
        Updated user data
    """
    # Prepare update data
    update_data = user.dict(exclude_unset=True)
    
    # Hash password if provided
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    
    # Update user
    updated_user = await firestore_service.update_user(user_id, update_data)
    return updated_user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str = Path(...),
    current_user: dict = Depends(auth_service.get_current_user)
):
    """
    Delete a user.
    
    Args:
        user_id: User ID
        current_user: Current authenticated user
    """
    await firestore_service.delete_user(user_id)
    return None