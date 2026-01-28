"""
Full Google Drive authentication with the 'drive' scope.

This module is now a thin wrapper around the main auth module,
maintained for backwards compatibility.
"""

import logging
from typing import Optional

from .auth import (
    get_credentials,
    get_drive_service,
    reset_auth,
    GoogleAuthError,
)

logger = logging.getLogger(__name__)


# Backwards compatibility alias
FullDriveAuthError = GoogleAuthError


def get_full_drive_token(force_refresh: bool = False) -> str:
    """Get a token with full Google Drive access.

    This function is maintained for backwards compatibility.
    The main auth module now uses full 'drive' scope by default.

    Args:
        force_refresh: If True, get a new token even if cached.

    Returns:
        str: The access token.

    Raises:
        FullDriveAuthError: If authentication fails.
    """
    credentials = get_credentials(force_refresh=force_refresh)
    return credentials.token


def clear_token_cache() -> None:
    """Clear the cached full Drive token.

    Use this when you need to force re-authentication.
    """
    reset_auth()
    logger.debug("Cleared full Drive token cache")


def is_token_cached() -> bool:
    """Check if a full Drive token is cached.

    Returns:
        bool: True if a token is cached.
    """
    try:
        from .auth import _credentials
        return _credentials is not None and _credentials.valid
    except ImportError:
        return False
