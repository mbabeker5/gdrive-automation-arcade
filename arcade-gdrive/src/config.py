"""
Configuration management with lazy loading to avoid import-time failures.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    """Configuration for Arcade Google Drive operations."""

    arcade_api_key: str
    arcade_user_id: str
    default_parent_folder_id: Optional[str] = None
    default_shared_drive_id: Optional[str] = None

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables.

        Raises:
            ValueError: If required environment variables are missing.
        """
        api_key = os.getenv("ARCADE_API_KEY")
        user_id = os.getenv("ARCADE_USER_ID")

        if not api_key:
            raise ValueError(
                "ARCADE_API_KEY environment variable is required. "
                "Get your API key from https://arcade.dev"
            )

        if not user_id:
            raise ValueError(
                "ARCADE_USER_ID environment variable is required. "
                "This should be your email address."
            )

        return cls(
            arcade_api_key=api_key,
            arcade_user_id=user_id,
            default_parent_folder_id=os.getenv("DEFAULT_PARENT_FOLDER_ID"),
            default_shared_drive_id=os.getenv("DEFAULT_SHARED_DRIVE_ID"),
        )


# Lazy-loaded singleton config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the configuration singleton, loading from environment if needed.

    This function implements lazy loading to avoid import-time failures
    when environment variables are not yet set.

    Returns:
        Config: The configuration instance.

    Raises:
        ValueError: If required environment variables are missing.
    """
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def reset_config() -> None:
    """Reset the configuration singleton.

    Useful for testing or when environment variables change.
    """
    global _config
    _config = None


def load_dotenv_if_exists() -> bool:
    """Load .env file if it exists.

    Returns:
        bool: True if .env file was loaded, False otherwise.
    """
    try:
        from dotenv import load_dotenv

        # Try to find .env in current directory or parent directories
        env_path = Path(".env")
        if not env_path.exists():
            # Try project root
            project_root = Path(__file__).parent.parent
            env_path = project_root / ".env"

        if env_path.exists():
            load_dotenv(env_path)
            return True
        return False
    except ImportError:
        return False


# Auto-load .env file when module is imported
load_dotenv_if_exists()
