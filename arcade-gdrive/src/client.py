"""
High-level Google Drive client for common operations.

This module provides a convenient DriveClient class that wraps all the
individual drive operations into a single, easy-to-use interface.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from .config import load_dotenv_if_exists, get_config
from .auth import get_arcade_client, execute_tool, ArcadeToolError
from .drive import (
    # Search
    search,
    find_by_name,
    find_by_id,
    get_url_by_id,
    list_shared_drives,
    SearchResult,
    FileInfo,
    # Folders
    create_folder,
    create_nested_folders,
    FolderResult,
    # Sharing
    share_with_users,
    create_folder_and_share,
    create_folder_and_get_url,
    ShareResult,
    UrlResult,
    # Download
    download_file,
    download_to_memory,
    DownloadResult,
    # Utils
    build_drive_url,
    parse_file_id,
)

logger = logging.getLogger(__name__)


class DriveClient:
    """High-level client for Google Drive operations via Arcade.

    This class provides a convenient interface for common Drive operations
    including searching, creating folders, sharing, and downloading files.

    Example:
        ```python
        from src.client import DriveClient

        client = DriveClient()

        # Search for files
        results = client.search("quarterly report")
        for file in results.files:
            print(f"{file.name}: {file.url}")

        # Create and share a folder
        result = client.create_folder_and_share(
            "Project Files",
            emails=["colleague@example.com"],
            role="writer",
        )
        print(f"Folder URL: {result.folder_url}")
        ```
    """

    def __init__(self, load_env: bool = True):
        """Initialize the Drive client.

        Args:
            load_env: If True, load .env file if present.
        """
        if load_env:
            load_dotenv_if_exists()

        # Validate configuration is available
        self._config = get_config()
        logger.debug(f"DriveClient initialized for user: {self._config.arcade_user_id}")

    @property
    def user_id(self) -> str:
        """Get the configured Arcade user ID."""
        return self._config.arcade_user_id

    # -------------------------------------------------------------------------
    # Search operations
    # -------------------------------------------------------------------------

    def search(
        self,
        query: str,
        max_results: int = 100,
        file_type: Optional[str] = None,
        parent_id: Optional[str] = None,
    ) -> SearchResult:
        """Search for files and folders.

        Args:
            query: Search query string.
            max_results: Maximum number of results.
            file_type: Optional filter for file type.
            parent_id: Optional parent folder to search within.

        Returns:
            SearchResult: Search results.
        """
        return search(query, max_results, file_type, parent_id)

    def find_by_name(
        self,
        name: str,
        exact_match: bool = True,
        file_type: Optional[str] = None,
    ) -> SearchResult:
        """Find files or folders by name.

        Args:
            name: Name to search for.
            exact_match: Only return exact matches.
            file_type: Optional file type filter.

        Returns:
            SearchResult: Matching files.
        """
        return find_by_name(name, exact_match, file_type)

    def find_by_id(self, file_id: str, assume_folder: Optional[bool] = None) -> Optional[FileInfo]:
        """Find a file or folder by ID.

        Note: This may not work reliably for all files. Use get_url_by_id()
        if you just need the URL.

        Args:
            file_id: The file or folder ID.
            assume_folder: If True, assume it's a folder for URL construction.

        Returns:
            FileInfo if found, None otherwise.
        """
        return find_by_id(file_id, assume_folder)

    def get_url_by_id(self, file_id: str, is_folder: bool = False) -> str:
        """Get the Drive URL for a file or folder ID.

        This constructs the URL directly without API calls.

        Args:
            file_id: The file or folder ID.
            is_folder: True if it's a folder.

        Returns:
            str: The Google Drive URL.
        """
        return get_url_by_id(file_id, is_folder)

    def list_shared_drives(self) -> SearchResult:
        """List all accessible Shared Drives.

        Returns:
            SearchResult: List of Shared Drives.
        """
        return list_shared_drives()

    # -------------------------------------------------------------------------
    # Folder operations
    # -------------------------------------------------------------------------

    def create_folder(
        self,
        name: str,
        parent_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> FolderResult:
        """Create a new folder.

        Args:
            name: Folder name.
            parent_id: Optional parent folder ID.
            description: Optional folder description.

        Returns:
            FolderResult: Result with folder ID and URL.
        """
        parent = parent_id or self._config.default_parent_folder_id
        return create_folder(name, parent_id=parent, description=description)

    def create_nested_folders(
        self,
        path: str,
        root_parent_id: Optional[str] = None,
    ) -> FolderResult:
        """Create nested folders from a path.

        Args:
            path: Path like "parent/child/grandchild".
            root_parent_id: Optional root parent folder ID.

        Returns:
            FolderResult: Result for the deepest folder.
        """
        parent = root_parent_id or self._config.default_parent_folder_id
        return create_nested_folders(path, root_parent_id=parent)

    # -------------------------------------------------------------------------
    # Sharing operations
    # -------------------------------------------------------------------------

    def share(
        self,
        file_id: str,
        emails: list[str],
        role: str = "reader",
        send_notification: bool = True,
    ) -> ShareResult:
        """Share a file or folder with users.

        Args:
            file_id: ID of the file or folder.
            emails: Email addresses to share with.
            role: Permission role (reader, writer, commenter).
            send_notification: Send email notifications.

        Returns:
            ShareResult: Sharing result.
        """
        return share_with_users(file_id, emails, role, send_notification)

    def create_folder_and_share(
        self,
        name: str,
        emails: list[str],
        parent_id: Optional[str] = None,
        role: str = "reader",
    ) -> FolderResult:
        """Create a folder and share it.

        Args:
            name: Folder name.
            emails: Emails to share with.
            parent_id: Optional parent folder ID.
            role: Permission role.

        Returns:
            FolderResult: Result including sharing status.
        """
        parent = parent_id or self._config.default_parent_folder_id
        return create_folder_and_share(name, emails, parent_id=parent, role=role)

    def create_folder_and_get_url(
        self,
        name: str,
        parent_id: Optional[str] = None,
        share_with: Optional[list[str]] = None,
        role: str = "reader",
    ) -> UrlResult:
        """Create a folder and get its URL.

        Args:
            name: Folder name.
            parent_id: Optional parent folder ID.
            share_with: Optional emails to share with.
            role: Permission role for sharing.

        Returns:
            UrlResult: Result with URL and sharing status.
        """
        parent = parent_id or self._config.default_parent_folder_id
        return create_folder_and_get_url(name, parent_id=parent, share_with=share_with, role=role)

    # -------------------------------------------------------------------------
    # Download operations
    # -------------------------------------------------------------------------

    def download(
        self,
        file_id: str,
        output_path: str | Path,
    ) -> DownloadResult:
        """Download a file to disk.

        Args:
            file_id: ID of the file to download.
            output_path: Local path to save the file.

        Returns:
            DownloadResult: Download result.
        """
        return download_file(file_id, output_path)

    def download_to_memory(
        self,
        file_id: str,
        max_size_mb: int = 100,
    ) -> tuple[bool, bytes | str]:
        """Download a file to memory.

        Args:
            file_id: ID of the file.
            max_size_mb: Maximum file size in MB.

        Returns:
            tuple: (success, data or error message)
        """
        return download_to_memory(file_id, max_size_mb)

    # -------------------------------------------------------------------------
    # Utility methods
    # -------------------------------------------------------------------------

    def parse_file_id(self, url_or_id: str) -> str:
        """Extract file ID from a URL or return the ID.

        Args:
            url_or_id: Drive URL or file ID.

        Returns:
            str: The file ID.
        """
        return parse_file_id(url_or_id)

    def build_url(self, file_id: str, is_folder: bool = False) -> str:
        """Build a Drive URL from an ID.

        Args:
            file_id: File or folder ID.
            is_folder: True if it's a folder.

        Returns:
            str: The Drive URL.
        """
        return build_drive_url(file_id, is_folder)

    def get_user_info(self) -> dict:
        """Get information about the authenticated user.

        Returns:
            dict: User information including email and name.
        """
        try:
            result = execute_tool("GoogleDrive.WhoAmI")
            return result if isinstance(result, dict) else {"raw": result}
        except ArcadeToolError as e:
            return {"error": str(e)}


# Convenience function to create a client
def create_client(load_env: bool = True) -> DriveClient:
    """Create a DriveClient instance.

    Args:
        load_env: If True, load .env file if present.

    Returns:
        DriveClient: Configured client instance.
    """
    return DriveClient(load_env=load_env)
