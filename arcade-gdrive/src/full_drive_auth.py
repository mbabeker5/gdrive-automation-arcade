"""
Full Google Drive authentication with the 'drive' scope.

This module uses client.auth.start() with explicit scopes to get a token
with full Drive access (not just app-created files). This is necessary
for accessing Shared Drives and existing files.
"""

import logging
from typing import Optional

from arcadepy import Arcade

from .config import get_config

logger = logging.getLogger(__name__)

# Cache for the full-access token
_full_drive_token: Optional[str] = None

# Scopes required for full Drive access
FULL_DRIVE_SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]


class FullDriveAuthError(Exception):
    """Raised when full Drive authentication fails."""
    pass


def get_full_drive_token(force_refresh: bool = False) -> str:
    """Get a token with full Google Drive access.

    Uses client.auth.start() with explicit scopes to request the full
    'drive' scope, which gives access to ALL files in Drive (not just
    app-created files like drive.file scope).

    Args:
        force_refresh: If True, get a new token even if cached.

    Returns:
        str: The access token.

    Raises:
        FullDriveAuthError: If authentication fails.
    """
    global _full_drive_token

    if _full_drive_token is not None and not force_refresh:
        logger.debug("Using cached full Drive token")
        return _full_drive_token

    config = get_config()
    client = Arcade(api_key=config.arcade_api_key)

    try:
        logger.info("Starting full Drive authorization flow...")

        auth_response = client.auth.start(
            user_id=config.arcade_user_id,
            provider="google",
            scopes=FULL_DRIVE_SCOPES,
        )

        if auth_response.status != "completed":
            print("\n" + "=" * 60)
            print("Authorization required for full Google Drive access")
            print("=" * 60)
            print("\nPlease complete authorization in your browser:")
            print(auth_response.url)
            print("\nWaiting for authorization...")

            auth_response = client.auth.wait_for_completion(auth_response)

        if auth_response.status != "completed":
            raise FullDriveAuthError(
                f"Authorization failed. Status: {auth_response.status}"
            )

        token = auth_response.context.token
        if not token:
            raise FullDriveAuthError("No token received from authorization")

        _full_drive_token = token
        logger.info("Full Drive authorization successful")
        return token

    except FullDriveAuthError:
        raise
    except Exception as e:
        logger.error(f"Full Drive authorization failed: {e}")
        raise FullDriveAuthError(f"Authorization failed: {e}") from e


def clear_token_cache() -> None:
    """Clear the cached full Drive token.

    Use this when you need to force re-authentication.
    """
    global _full_drive_token
    _full_drive_token = None
    logger.debug("Cleared full Drive token cache")


def is_token_cached() -> bool:
    """Check if a full Drive token is cached.

    Returns:
        bool: True if a token is cached.
    """
    return _full_drive_token is not None
