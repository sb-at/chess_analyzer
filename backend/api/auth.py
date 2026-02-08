"""Authentication API routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db
from models import User
from auth import (
    ChessComOAuth,
    LichessOAuth,
    create_access_token,
    create_refresh_token,
    get_current_user
)
import uuid

router = APIRouter()


class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class OAuthCallbackRequest(BaseModel):
    """OAuth callback request model."""
    code: str
    state: Optional[str] = None


@router.get("/chess-com/authorize")
async def chess_com_authorize():
    """Get Chess.com OAuth authorization URL."""
    oauth = ChessComOAuth()
    state = str(uuid.uuid4())
    auth_url = oauth.get_authorization_url(state=state)
    return {"auth_url": auth_url, "state": state}


@router.post("/chess-com/callback", response_model=TokenResponse)
async def chess_com_callback(
    request: OAuthCallbackRequest,
    db: Session = Depends(get_db)
):
    """Handle Chess.com OAuth callback."""
    oauth = ChessComOAuth()

    # Exchange code for token
    token_data = await oauth.exchange_code_for_token(request.code)
    access_token = token_data.get("access_token")

    # For Chess.com, we need to extract username differently
    # The username might be in the token response or we need to call an endpoint
    # For now, we'll need the client to provide it or get it from profile
    # This is a simplified version

    # TODO: Get actual username from Chess.com API
    username = "placeholder_username"  # Replace with actual username extraction

    # Find or create user
    user = db.query(User).filter(User.chess_com_username == username).first()

    if not user:
        user = User(
            chess_com_username=username,
            chess_com_access_token=access_token
        )
        db.add(user)
    else:
        user.chess_com_access_token = access_token

    db.commit()
    db.refresh(user)

    # Create JWT tokens
    jwt_access_token = create_access_token({"sub": str(user.id)})
    jwt_refresh_token = create_refresh_token({"sub": str(user.id)})

    return TokenResponse(
        access_token=jwt_access_token,
        refresh_token=jwt_refresh_token,
        user={
            "id": str(user.id),
            "chess_com_username": user.chess_com_username,
            "lichess_username": user.lichess_username
        }
    )


@router.get("/lichess/authorize")
async def lichess_authorize():
    """Get Lichess OAuth authorization URL."""
    oauth = LichessOAuth()
    state = str(uuid.uuid4())
    auth_url = oauth.get_authorization_url(state=state)
    return {"auth_url": auth_url, "state": state}


@router.post("/lichess/callback", response_model=TokenResponse)
async def lichess_callback(
    request: OAuthCallbackRequest,
    db: Session = Depends(get_db)
):
    """Handle Lichess OAuth callback."""
    oauth = LichessOAuth()

    # Exchange code for token
    token_data = await oauth.exchange_code_for_token(request.code)
    access_token = token_data.get("access_token")

    # Get user info
    user_info = await oauth.get_user_info(access_token)
    username = user_info.get("username", "").lower()

    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not retrieve username from Lichess"
        )

    # Find or create user
    user = db.query(User).filter(User.lichess_username == username).first()

    if not user:
        user = User(
            lichess_username=username,
            lichess_access_token=access_token
        )
        db.add(user)
    else:
        user.lichess_access_token = access_token

    db.commit()
    db.refresh(user)

    # Create JWT tokens
    jwt_access_token = create_access_token({"sub": str(user.id)})
    jwt_refresh_token = create_refresh_token({"sub": str(user.id)})

    return TokenResponse(
        access_token=jwt_access_token,
        refresh_token=jwt_refresh_token,
        user={
            "id": str(user.id),
            "chess_com_username": user.chess_com_username,
            "lichess_username": user.lichess_username
        }
    )


@router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "chess_com_username": current_user.chess_com_username,
        "lichess_username": current_user.lichess_username,
        "rating": current_user.rating,
        "created_at": current_user.created_at,
        "last_sync": current_user.last_sync
    }
