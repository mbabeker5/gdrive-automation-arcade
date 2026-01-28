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
from .auth import get_drive_service, GoogleAuthError
from .drive import (
    # Search
    search,
    find_by_name,
    find_by_id,
    get_url_by_id,
    list_shared_drives,
    get_file_tree_structure,
    get_user_info,
    generate_file_picker_url,
    SearchResult,
    FileInfo,
    TreeNode,
    TreeResult,
    UserInfo,
    # Files
    rename_file,
    upload_file,
    FileResult,
    UploadResult,
    # Folders
    create_folder,
    create_nested_folders,
    move_to_folder,
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
# Full Drive access imports (for Shared Drives and existing files)
from .drive.google_api import (
    search_all,
    list_folder_contents,
    create_folder_in_shared_drive,
    delete_file as google_delete_file,
    get_shared_drives,
    SearchAllResult,
    ListContentsResult,
    FolderCreateResult as GoogleFolderResult,
    DriveFile,
)

logger = logging.getLogger(__name__)


class DriveClient:
    """High-level client for Google Drive operations.

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
        logger.debug("DriveClient initialized")

    # -------------------------------------------------------------------------
    # Search operations
    # -------------------------------------------------------------------------

    def search(
        self,
        query: str,
        max_results: int = 100,
        file_type: Optional[str] = None,
        parent_id: Optional[str] = None,
        include_shared_drives: bool = False,
        shared_drive_id: Optional[str] = None,
        include_organization_domain_documents: bool = False,
        order_by: Optional[str] = None,
    ) -> SearchResult:
        """Search for files and folders.

        Args:
            query: Search query string.
            max_results: Maximum number of results.
            file_type: Optional filter for file type.
            parent_id: Optional parent folder to search within.
            include_shared_drives: Include files from Shared Drives.
            shared_drive_id: Limit search to a specific Shared Drive.
            include_organization_domain_documents: Include organization domain documents.
            order_by: Ordering for results.

        Returns:
            SearchResult: Search results.
        """
        return search(
            query,
            max_results,
            file_type,
            parent_id,
            include_shared_drives,
            shared_drive_id,
            include_organization_domain_documents,
            order_by,
        )

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
        message: Optional[str] = None,
    ) -> ShareResult:
        """Share a file or folder with users.

        Args:
            file_id: ID of the file or folder.
            emails: Email addresses to share with.
            role: Permission role (reader, writer, commenter).
            send_notification: Send email notifications.
            message: Optional custom message for notification email.

        Returns:
            ShareResult: Sharing result.
        """
        return share_with_users(file_id, emails, role, send_notification, message)

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
        from .drive.google_api import get_user_info as google_get_user_info
        return google_get_user_info()

    def get_full_user_info(self) -> UserInfo:
        """Get full user profile and Drive environment information.

        Returns:
            UserInfo: Full user information including email, name, and shared drives.
        """
        return get_user_info()

    # -------------------------------------------------------------------------
    # File operations
    # -------------------------------------------------------------------------

    def rename(
        self,
        file_id: str,
        new_name: str,
        shared_drive_id: Optional[str] = None,
    ) -> FileResult:
        """Rename a file or folder.

        Args:
            file_id: ID of the file or folder to rename.
            new_name: New name for the file or folder.
            shared_drive_id: Optional Shared Drive ID.

        Returns:
            FileResult: Result with file ID and URL.
        """
        return rename_file(file_id, new_name, shared_drive_id)

    def upload(
        self,
        file_name: str,
        source_url: str,
        mime_type: Optional[str] = None,
        destination_folder_id: Optional[str] = None,
        shared_drive_id: Optional[str] = None,
    ) -> UploadResult:
        """Upload a file from a URL.

        Args:
            file_name: Name for the uploaded file.
            source_url: URL to download the file from.
            mime_type: Optional MIME type.
            destination_folder_id: Optional destination folder ID.
            shared_drive_id: Optional Shared Drive ID.

        Returns:
            UploadResult: Result with file ID, URL, and name.
        """
        folder_id = destination_folder_id or self._config.default_parent_folder_id
        return upload_file(file_name, source_url, mime_type, folder_id, shared_drive_id)

    def move(
        self,
        file_id: str,
        new_parent_id: str,
        new_filename: Optional[str] = None,
    ) -> FolderResult:
        """Move a file or folder to a new parent folder.

        Args:
            file_id: ID of the file or folder to move.
            new_parent_id: ID of the destination folder.
            new_filename: Optional new name for the file after moving.

        Returns:
            FolderResult: Result of the operation.
        """
        return move_to_folder(file_id, new_parent_id, new_filename=new_filename)

    # -------------------------------------------------------------------------
    # Tree and picker operations
    # -------------------------------------------------------------------------

    def get_file_tree(
        self,
        include_shared_drives: bool = False,
        restrict_to_shared_drive_id: Optional[str] = None,
        limit: Optional[int] = 100,
    ) -> TreeResult:
        """Get the file/folder tree structure.

        WARNING: Can be inefficient for large drives. Use limit parameter.

        Args:
            include_shared_drives: Include files from Shared Drives.
            restrict_to_shared_drive_id: Limit to a specific Shared Drive.
            limit: Maximum number of items to return.

        Returns:
            TreeResult: The file tree structure.
        """
        return get_file_tree_structure(
            include_shared_drives=include_shared_drives,
            restrict_to_shared_drive_id=restrict_to_shared_drive_id,
            limit=limit,
        )

    def get_file_picker_url(self) -> str:
        """Generate a Google File Picker URL.

        Returns:
            str: The File Picker URL.
        """
        return generate_file_picker_url()

    # -------------------------------------------------------------------------
    # Full Drive Access operations (Shared Drives and existing files)
    # -------------------------------------------------------------------------
    # These methods use direct Google API calls with full 'drive' scope,
    # allowing access to ALL files (not just app-created files).

    def search_shared_drive(
        self,
        query: str,
        *,
        file_type: Optional[str] = None,
        max_results: int = 100,
    ) -> SearchAllResult:
        """Search across all drives including Shared Drives.

        Uses full Drive access to search ALL files, not just app-created ones.

        Args:
            query: Search term (searches file names).
            file_type: Optional filter - "folder", "document", "spreadsheet", etc.
            max_results: Maximum results to return.

        Returns:
            SearchAllResult: Search results.

        Example:
            >>> result = client.search_shared_drive("[20] Build", file_type="folder")
            >>> if result.success:
            ...     for f in result.files:
            ...         print(f"{f.name}: {f.web_view_link}")
        """
        return search_all(query, file_type=file_type, max_results=max_results)

    def list_folder(self, folder_id: str) -> ListContentsResult:
        """List contents of a folder (files and subfolders).

        Uses full Drive access to list ALL files in the folder.

        Args:
            folder_id: The folder ID.

        Returns:
            ListContentsResult: Folder contents.

        Example:
            >>> result = client.list_folder("abc123")
            >>> for f in result.files:
            ...     kind = "folder" if f.is_folder else "file"
            ...     print(f"[{kind}] {f.name}")
        """
        return list_folder_contents(folder_id)

    def create_folder_shared_drive(
        self,
        name: str,
        parent_id: str,
        drive_id: Optional[str] = None,
    ) -> GoogleFolderResult:
        """Create a folder in a Shared Drive.

        Uses full Drive access with supportsAllDrives=True.

        Args:
            name: Name for the new folder.
            parent_id: Parent folder ID.
            drive_id: Shared Drive ID (optional, for explicit Shared Drive support).

        Returns:
            FolderCreateResult: Creation result.

        Example:
            >>> result = client.create_folder_shared_drive("[47] Build", parent_id="abc123")
            >>> if result.success:
            ...     print(f"Created: {result.web_view_link}")
        """
        return create_folder_in_shared_drive(name, parent_id, drive_id=drive_id)

    def delete(self, file_id: str) -> bool:
        """Delete a file or folder.

        Args:
            file_id: ID of the file or folder to delete.

        Returns:
            bool: True if successful.
        """
        return google_delete_file(file_id)

    def get_all_shared_drives(self) -> list[DriveFile]:
        """List all accessible Shared Drives using full Drive access.

        Returns:
            List[DriveFile]: List of Shared Drives.

        Example:
            >>> drives = client.get_all_shared_drives()
            >>> for d in drives:
            ...     print(f"{d.name}: {d.id}")
        """
        return get_shared_drives()


# Convenience function to create a client
def create_client(load_env: bool = True) -> DriveClient:
    """Create a DriveClient instance.

    Args:
        load_env: If True, load .env file if present.

    Returns:
        DriveClient: Configured client instance.
    """
    return DriveClient(load_env=load_env)
