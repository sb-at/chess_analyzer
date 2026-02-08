"""OAuth handlers for Chess.com and Lichess."""
import httpx
from typing import Optional
from fastapi import HTTPException
from config import get_settings

settings = get_settings()


class ChessComOAuth:
    """Chess.com OAuth handler."""

    def __init__(self):
        self.client_id = settings.chess_com_client_id
        self.client_secret = settings.chess_com_client_secret
        self.redirect_uri = settings.chess_com_redirect_uri
        self.authorize_url = "https://oauth.chess.com/oauth/authorize"
        self.token_url = "https://oauth.chess.com/oauth/token"
        self.api_base = "https://api.chess.com/pub"

    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """Get OAuth authorization URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "read"
        }
        if state:
            params["state"] = state

        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.authorize_url}?{query_string}"

    async def exchange_code_for_token(self, code: str) -> dict:
        """Exchange authorization code for access token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.redirect_uri
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to get access token: {response.text}"
                )

            return response.json()

    async def get_user_info(self, access_token: str) -> dict:
        """Get user information using access token."""
        # Chess.com doesn't have a standard user info endpoint
        # We'll need to get username from the token response or use profile endpoint
        # For now, return basic structure
        return {"platform": "chess.com"}


class LichessOAuth:
    """Lichess OAuth handler."""

    def __init__(self):
        self.client_id = settings.lichess_client_id
        self.redirect_uri = settings.lichess_redirect_uri
        self.authorize_url = "https://lichess.org/oauth"
        self.token_url = "https://lichess.org/api/token"
        self.api_base = "https://lichess.org/api"

    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """Get OAuth authorization URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "challenge:read"
        }
        if state:
            params["state"] = state

        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.authorize_url}?{query_string}"

    async def exchange_code_for_token(self, code: str) -> dict:
        """Exchange authorization code for access token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": self.client_id,
                    "redirect_uri": self.redirect_uri,
                    "code_verifier": "not_implemented"  # TODO: Implement PKCE
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to get access token: {response.text}"
                )

            return response.json()

    async def get_user_info(self, access_token: str) -> dict:
        """Get user information using access token."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base}/account",
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail="Failed to get user info"
                )

            return response.json()
