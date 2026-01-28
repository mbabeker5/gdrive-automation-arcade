"""
Configuration management with lazy loading to avoid import-time failures.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    """Configuration for Google Drive operations."""

    google_credentials_file: str
    google_token_file: str
    default_parent_folder_id: Optional[str] = None
    default_shared_drive_id: Optional[str] = None

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables.

        Returns:
            Config: Configuration instance.
        """
        return cls(
            google_credentials_file=os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json"),
            google_token_file=os.getenv("GOOGLE_TOKEN_FILE", "token.json"),
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
