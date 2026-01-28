"""
Direct Google Drive API operations using full Drive access token.

This module provides direct API calls to Google Drive using the token
obtained with full 'drive' scope, allowing access to:
- All files in My Drive
- All files in Shared Drives
- Files created by other apps
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional, List

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from ..full_drive_auth import get_full_drive_token, FullDriveAuthError

logger = logging.getLogger(__name__)


@dataclass
class DriveFile:
    """Represents a file or folder from Google Drive."""
    id: str
    name: str
    mime_type: str
    web_view_link: Optional[str] = None
    parents: List[str] = field(default_factory=list)
    drive_id: Optional[str] = None

    @property
    def is_folder(self) -> bool:
        """Check if this is a folder."""
        return self.mime_type == "application/vnd.google-apps.folder"

    @property
    def is_shared_drive(self) -> bool:
        """Check if this file is in a Shared Drive."""
        return self.drive_id is not None


@dataclass
class SearchAllResult:
    """Result of a search across all drives."""
    success: bool
    files: List[DriveFile] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def count(self) -> int:
        """Get the number of files found."""
        return len(self.files)

    def folders(self) -> List[DriveFile]:
        """Get only folders from results."""
        return [f for f in self.files if f.is_folder]

    def first(self) -> Optional[DriveFile]:
        """Get the first result or None."""
        return self.files[0] if self.files else None


@dataclass
class FolderCreateResult:
    """Result of creating a folder."""
    success: bool
    folder_id: Optional[str] = None
    folder_name: Optional[str] = None
    web_view_link: Optional[str] = None
    error: Optional[str] = None


@dataclass
class ListContentsResult:
    """Result of listing folder contents."""
    success: bool
    files: List[DriveFile] = field(default_factory=list)
    folder_name: Optional[str] = None
    error: Optional[str] = None

    @property
    def count(self) -> int:
        """Get the number of items."""
        return len(self.files)


def _get_drive_service():
    """Get an authenticated Google Drive service.

    Returns:
        googleapiclient.discovery.Resource: The Drive API service.

    Raises:
        FullDriveAuthError: If authentication fails.
    """
    token = get_full_drive_token()
    credentials = Credentials(token)
    return build("drive", "v3", credentials=credentials)


def search_all(
    query: str,
    *,
    file_type: Optional[str] = None,
    in_shared_drives: bool = True,
    max_results: int = 100,
) -> SearchAllResult:
    """Search for files across all drives including Shared Drives.

    This uses the full 'drive' scope to search ALL accessible files,
    not just app-created files.

    Args:
        query: Search term (searches file names).
        file_type: Optional filter - "folder", "document", "spreadsheet", etc.
        in_shared_drives: Include Shared Drives in search.
        max_results: Maximum results to return.

    Returns:
        SearchAllResult: Search results.

    Example:
        >>> result = search_all("[20] Build", file_type="folder")
        >>> for f in result.files:
        ...     print(f"{f.name}: {f.web_view_link}")
    """
    try:
        service = _get_drive_service()

        # Build query
        q_parts = [f"name contains '{query}'"]

        if file_type:
            mime_type_map = {
                "folder": "application/vnd.google-apps.folder",
                "document": "application/vnd.google-apps.document",
                "spreadsheet": "application/vnd.google-apps.spreadsheet",
                "presentation": "application/vnd.google-apps.presentation",
                "pdf": "application/pdf",
            }
            if file_type in mime_type_map:
                q_parts.append(f"mimeType = '{mime_type_map[file_type]}'")

        q = " and ".join(q_parts)

        results = service.files().list(
            q=q,
            spaces="drive",
            includeItemsFromAllDrives=in_shared_drives,
            supportsAllDrives=in_shared_drives,
            pageSize=min(max_results, 1000),
            fields="files(id, name, mimeType, webViewLink, parents, driveId)"
        ).execute()

        files = []
        for item in results.get("files", []):
            files.append(DriveFile(
                id=item.get("id", ""),
                name=item.get("name", ""),
                mime_type=item.get("mimeType", ""),
                web_view_link=item.get("webViewLink"),
                parents=item.get("parents", []),
                drive_id=item.get("driveId"),
            ))

        return SearchAllResult(success=True, files=files)

    except FullDriveAuthError as e:
        return SearchAllResult(success=False, error=str(e))
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return SearchAllResult(success=False, error=str(e))


def list_folder_contents(
    folder_id: str,
    *,
    in_shared_drives: bool = True,
) -> ListContentsResult:
    """List all files and folders inside a folder.

    Args:
        folder_id: The ID of the folder to list.
        in_shared_drives: Support Shared Drives.

    Returns:
        ListContentsResult: Folder contents.

    Example:
        >>> result = list_folder_contents("abc123")
        >>> for f in result.files:
        ...     kind = "folder" if f.is_folder else "file"
        ...     print(f"[{kind}] {f.name}")
    """
    try:
        service = _get_drive_service()

        # First get folder info
        folder_info = service.files().get(
            fileId=folder_id,
            supportsAllDrives=in_shared_drives,
            fields="name"
        ).execute()

        folder_name = folder_info.get("name", "Unknown")

        # List contents
        q = f"'{folder_id}' in parents and trashed = false"

        results = service.files().list(
            q=q,
            includeItemsFromAllDrives=in_shared_drives,
            supportsAllDrives=in_shared_drives,
            fields="files(id, name, mimeType, webViewLink, parents, driveId)"
        ).execute()

        files = []
        for item in results.get("files", []):
            files.append(DriveFile(
                id=item.get("id", ""),
                name=item.get("name", ""),
                mime_type=item.get("mimeType", ""),
                web_view_link=item.get("webViewLink"),
                parents=item.get("parents", []),
                drive_id=item.get("driveId"),
            ))

        return ListContentsResult(
            success=True,
            files=files,
            folder_name=folder_name,
        )

    except FullDriveAuthError as e:
        return ListContentsResult(success=False, error=str(e))
    except Exception as e:
        logger.error(f"List folder contents failed: {e}")
        return ListContentsResult(success=False, error=str(e))


def create_folder_in_shared_drive(
    name: str,
    parent_id: str,
    *,
    drive_id: Optional[str] = None,
) -> FolderCreateResult:
    """Create a folder in a Shared Drive.

    Args:
        name: Name for the new folder.
        parent_id: Parent folder ID.
        drive_id: Shared Drive ID (required for Shared Drives).

    Returns:
        FolderCreateResult: Creation result.

    Example:
        >>> result = create_folder_in_shared_drive(
        ...     "[47] Build",
        ...     parent_id="abc123",
        ...     drive_id="def456"
        ... )
        >>> if result.success:
        ...     print(f"Created: {result.web_view_link}")
    """
    try:
        service = _get_drive_service()

        file_metadata = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id],
        }

        # If drive_id provided, include it for Shared Drive support
        if drive_id:
            file_metadata["driveId"] = drive_id

        folder = service.files().create(
            body=file_metadata,
            supportsAllDrives=True,
            fields="id, name, webViewLink"
        ).execute()

        return FolderCreateResult(
            success=True,
            folder_id=folder.get("id"),
            folder_name=folder.get("name"),
            web_view_link=folder.get("webViewLink"),
        )

    except FullDriveAuthError as e:
        return FolderCreateResult(success=False, error=str(e))
    except Exception as e:
        logger.error(f"Create folder failed: {e}")
        return FolderCreateResult(success=False, error=str(e))


def delete_file(file_id: str, permanent: bool = False) -> bool:
    """Delete a file or folder (moves to trash by default).

    In Shared Drives, permanent deletion requires organizer permissions.
    Trashing is typically allowed for contributors.

    Args:
        file_id: ID of the file or folder to delete.
        permanent: If True, permanently delete (requires higher permissions).
                   If False (default), move to trash.

    Returns:
        bool: True if successful.
    """
    try:
        service = _get_drive_service()

        if permanent:
            service.files().delete(
                fileId=file_id,
                supportsAllDrives=True,
            ).execute()
        else:
            # Move to trash instead of permanent delete
            service.files().update(
                fileId=file_id,
                body={"trashed": True},
                supportsAllDrives=True,
            ).execute()

        return True
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        return False


def get_shared_drives() -> List[DriveFile]:
    """List all accessible Shared Drives.

    Returns:
        List[DriveFile]: List of Shared Drives.
    """
    try:
        service = _get_drive_service()

        results = service.drives().list(
            pageSize=100,
            fields="drives(id, name)"
        ).execute()

        drives = []
        for drive in results.get("drives", []):
            drives.append(DriveFile(
                id=drive.get("id", ""),
                name=drive.get("name", ""),
                mime_type="application/vnd.google-apps.folder",
                drive_id=drive.get("id"),
            ))

        return drives

    except Exception as e:
        logger.error(f"List shared drives failed: {e}")
        return []
