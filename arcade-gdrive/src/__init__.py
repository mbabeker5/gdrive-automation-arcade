"""
Google Drive Automation Toolkit

A modular Python toolkit for automating Google Drive operations using direct Google API.
"""

__version__ = "0.1.0"

from .auth import SCOPES, GoogleAuthError, get_drive_service, get_credentials, reset_auth

__all__ = [
    "SCOPES",
    "GoogleAuthError",
    "get_drive_service",
    "get_credentials",
    "reset_auth",
]
