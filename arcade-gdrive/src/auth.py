"""
Google Drive authentication using direct OAuth 2.0.

This module provides authentication for Google Drive API using standard
Google OAuth 2.0 flow, providing full Drive access (not just app-created files).
"""

import logging
import os
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource

logger = logging.getLogger(__name__)

# Scopes required for full Drive access
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]

# Singleton instances
_credentials: Optional[Credentials] = None
_service: Optional[Resource] = None


class GoogleAuthError(Exception):
    """Raised when Google authentication fails."""
    pass


class GoogleAPIError(Exception):
    """Raised when a Google API operation fails."""
    pass


def _get_credentials_path() -> Optional[Path]:
    """Get the path to the OAuth credentials file.

    Returns:
        Path to credentials.json file, or None if using env var credentials.

    Raises:
        GoogleAuthError: If credentials file is not found and no env var set.
    """
    # Check if credentials are provided via environment variable (for deployment)
    if os.getenv("GOOGLE_CREDENTIALS_JSON"):
        return None  # Signal to use env var instead of file

    # Check environment variable for file path
    creds_path = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")

    # Try multiple locations
    locations = [
        Path(creds_path),
        Path(__file__).parent.parent / creds_path,
        Path(__file__).parent.parent / "credentials.json",
        Path.home() / ".config" / "gdrive-automation" / "credentials.json",
    ]

    for loc in locations:
        if loc.exists():
            return loc

    raise GoogleAuthError(
        f"OAuth credentials file not found. Tried: {[str(l) for l in locations]}. "
        "Please download credentials.json from Google Cloud Console or set GOOGLE_CREDENTIALS_JSON env var."
    )


def _get_token_path() -> Path:
    """Get the path to store/load the OAuth token.

    Returns:
        Path to token.json file.
    """
    # Check environment variable first
    token_path = os.getenv("GOOGLE_TOKEN_FILE", "token.json")

    # Default to project root
    default_path = Path(__file__).parent.parent / token_path

    # If env var is an absolute path, use it
    if Path(token_path).is_absolute():
        return Path(token_path)

    return default_path


def get_credentials(force_refresh: bool = False) -> Credentials:
    """Get valid Google OAuth credentials.

    Uses cached credentials if available and valid. Otherwise, attempts
    to refresh or initiates the OAuth flow.

    Supports deployment via environment variables:
    - GOOGLE_TOKEN_JSON: JSON string of the token (from token.json content)

    Args:
        force_refresh: If True, ignore cached credentials and re-authenticate.

    Returns:
        Credentials: Valid Google OAuth credentials.

    Raises:
        GoogleAuthError: If authentication fails.
    """
    global _credentials

    if _credentials is not None and _credentials.valid and not force_refresh:
        return _credentials

    token_path = _get_token_path()

    # Try to load from environment variable first (for deployment)
    # Supports both GOOGLE_TOKEN_JSON (full JSON) and Streamlit secrets format
    token_json = os.getenv("GOOGLE_TOKEN_JSON")
    if token_json and not force_refresh:
        try:
            import json
            token_data = json.loads(token_json)
            _credentials = Credentials.from_authorized_user_info(token_data, SCOPES)
            logger.debug("Loaded credentials from GOOGLE_TOKEN_JSON env var")
        except Exception as e:
            logger.warning(f"Could not load credentials from env var: {e}")
            _credentials = None

    # Try Streamlit secrets format (for Streamlit Community Cloud)
    if _credentials is None and not force_refresh:
        try:
            import streamlit as st
            if hasattr(st, 'secrets') and 'google' in st.secrets:
                google_secrets = st.secrets['google']
                token_data = {
                    "token": google_secrets.get("token", ""),
                    "refresh_token": google_secrets.get("refresh_token", ""),
                    "token_uri": google_secrets.get("token_uri", "https://oauth2.googleapis.com/token"),
                    "client_id": google_secrets.get("client_id", ""),
                    "client_secret": google_secrets.get("client_secret", ""),
                    "scopes": list(google_secrets.get("scopes", SCOPES)),
                }
                _credentials = Credentials.from_authorized_user_info(token_data, SCOPES)
                logger.debug("Loaded credentials from Streamlit secrets")
        except Exception as e:
            logger.debug(f"Streamlit secrets not available: {e}")

    # Try to load saved credentials from file
    if _credentials is None and token_path.exists() and not force_refresh:
        try:
            _credentials = Credentials.from_authorized_user_file(str(token_path), SCOPES)
            logger.debug(f"Loaded credentials from {token_path}")
        except Exception as e:
            logger.warning(f"Could not load saved credentials: {e}")
            _credentials = None

    # Refresh if credentials exist but are expired
    if _credentials and _credentials.expired and _credentials.refresh_token:
        try:
            logger.info("Refreshing expired credentials...")
            _credentials.refresh(Request())
            # Only save to file if not using env var
            if not token_json:
                _save_credentials(_credentials, token_path)
            logger.info("Credentials refreshed successfully")
            return _credentials
        except Exception as e:
            logger.warning(f"Could not refresh credentials: {e}")
            _credentials = None

    # If no valid credentials, run the OAuth flow (only works locally)
    if not _credentials or not _credentials.valid:
        if os.getenv("GOOGLE_TOKEN_JSON"):
            raise GoogleAuthError(
                "Token from GOOGLE_TOKEN_JSON is invalid or expired. "
                "Please re-authenticate locally and update the env var."
            )
        _credentials = _run_oauth_flow()
        _save_credentials(_credentials, token_path)

    return _credentials


def _run_oauth_flow() -> Credentials:
    """Run the OAuth 2.0 authorization flow.

    Opens a browser for the user to authorize the application.

    Returns:
        Credentials: New OAuth credentials.

    Raises:
        GoogleAuthError: If the OAuth flow fails.
    """
    try:
        credentials_path = _get_credentials_path()
        logger.info(f"Starting OAuth flow with credentials from {credentials_path}")

        flow = InstalledAppFlow.from_client_secrets_file(
            str(credentials_path),
            SCOPES,
        )

        # Run local server for OAuth callback
        credentials = flow.run_local_server(
            port=0,  # Use any available port
            prompt="consent",  # Always show consent screen
            authorization_prompt_message="Please authorize access to Google Drive in your browser.",
        )

        logger.info("OAuth flow completed successfully")
        return credentials

    except Exception as e:
        raise GoogleAuthError(f"OAuth flow failed: {e}") from e


def _save_credentials(credentials: Credentials, token_path: Path) -> None:
    """Save credentials to a file for reuse.

    Args:
        credentials: Credentials to save.
        token_path: Path to save the credentials.
    """
    try:
        token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(token_path, "w") as f:
            f.write(credentials.to_json())
        logger.debug(f"Saved credentials to {token_path}")
    except Exception as e:
        logger.warning(f"Could not save credentials: {e}")


def get_drive_service(force_refresh: bool = False) -> Resource:
    """Get an authenticated Google Drive API service.

    Uses a singleton pattern to reuse the service instance.

    Args:
        force_refresh: If True, create a new service instance.

    Returns:
        Resource: Google Drive API service.

    Raises:
        GoogleAuthError: If authentication fails.
    """
    global _service

    if _service is not None and not force_refresh:
        return _service

    credentials = get_credentials(force_refresh=force_refresh)
    _service = build("drive", "v3", credentials=credentials)
    logger.debug("Created Drive API service")

    return _service


def reset_auth() -> None:
    """Reset cached credentials and service.

    Use this when you need to force re-authentication.
    """
    global _credentials, _service
    _credentials = None
    _service = None
    logger.debug("Reset authentication state")


def delete_token() -> bool:
    """Delete the stored token file to force re-authentication.

    Returns:
        bool: True if token was deleted, False if it didn't exist.
    """
    token_path = _get_token_path()
    if token_path.exists():
        token_path.unlink()
        reset_auth()
        logger.info(f"Deleted token file: {token_path}")
        return True
    return False


def get_user_email() -> Optional[str]:
    """Get the email address of the authenticated user.

    Returns:
        str: User's email address, or None if not available.
    """
    try:
        service = get_drive_service()
        about = service.about().get(fields="user").execute()
        return about.get("user", {}).get("emailAddress")
    except Exception as e:
        logger.warning(f"Could not get user email: {e}")
        return None


def is_authenticated() -> bool:
    """Check if valid credentials exist.

    Returns:
        bool: True if authenticated with valid credentials.
    """
    global _credentials

    if _credentials and _credentials.valid:
        return True

    token_path = _get_token_path()
    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
            return creds.valid or (creds.expired and creds.refresh_token)
        except Exception:
            pass

    return False
