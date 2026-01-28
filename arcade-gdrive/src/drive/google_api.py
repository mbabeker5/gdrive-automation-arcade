"""
Direct Google Drive API operations using full Drive access.

This module provides direct API calls to Google Drive allowing access to:
- All files in My Drive
- All files in Shared Drives
- Files created by other apps
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional, List

from ..auth import get_drive_service, GoogleAuthError, GoogleAPIError

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


@dataclass
class ShareResult:
    """Result of a sharing operation."""
    success: bool
    message: str
    permission_id: Optional[str] = None
    error: Optional[str] = None


@dataclass
class FileOperationResult:
    """Result of a file operation (rename, move, etc.)."""
    success: bool
    file_id: Optional[str] = None
    file_name: Optional[str] = None
    web_view_link: Optional[str] = None
    error: Optional[str] = None


def search_all(
    query: str,
    *,
    file_type: Optional[str] = None,
    in_shared_drives: bool = True,
    max_results: int = 100,
    parent_id: Optional[str] = None,
) -> SearchAllResult:
    """Search for files across all drives including Shared Drives.

    Args:
        query: Search term (searches file names).
        file_type: Optional filter - "folder", "document", "spreadsheet", etc.
        in_shared_drives: Include Shared Drives in search.
        max_results: Maximum results to return.
        parent_id: Optional parent folder ID to search within.

    Returns:
        SearchAllResult: Search results.

    Example:
        >>> result = search_all("[20] Build", file_type="folder")
        >>> for f in result.files:
        ...     print(f"{f.name}: {f.web_view_link}")
    """
    try:
        service = get_drive_service()

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

        if parent_id:
            q_parts.append(f"'{parent_id}' in parents")

        q_parts.append("trashed = false")
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

    except GoogleAuthError as e:
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
        service = get_drive_service()

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

    except GoogleAuthError as e:
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
        service = get_drive_service()

        file_metadata = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id],
        }

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

    except GoogleAuthError as e:
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
        service = get_drive_service()

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
        service = get_drive_service()

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


def share_file(
    file_id: str,
    email: str,
    role: str = "reader",
    send_notification: bool = True,
    message: Optional[str] = None,
) -> ShareResult:
    """Share a file or folder with a user.

    Args:
        file_id: ID of the file or folder to share.
        email: Email address to share with.
        role: Permission role - "reader", "writer", or "commenter".
        send_notification: Whether to send email notification.
        message: Optional message for the notification email.

    Returns:
        ShareResult: Result of the sharing operation.
    """
    try:
        service = get_drive_service()

        permission = {
            "type": "user",
            "role": role,
            "emailAddress": email,
        }

        result = service.permissions().create(
            fileId=file_id,
            body=permission,
            sendNotificationEmail=send_notification,
            emailMessage=message,
            supportsAllDrives=True,
        ).execute()

        return ShareResult(
            success=True,
            message=f"Shared with {email} as {role}",
            permission_id=result.get("id"),
        )

    except Exception as e:
        logger.error(f"Share failed: {e}")
        return ShareResult(
            success=False,
            message=str(e),
            error=str(e),
        )


def rename_file(
    file_id: str,
    new_name: str,
) -> FileOperationResult:
    """Rename a file or folder.

    Args:
        file_id: ID of the file or folder.
        new_name: New name.

    Returns:
        FileOperationResult: Result of the operation.
    """
    try:
        service = get_drive_service()

        result = service.files().update(
            fileId=file_id,
            body={"name": new_name},
            supportsAllDrives=True,
            fields="id, name, webViewLink"
        ).execute()

        return FileOperationResult(
            success=True,
            file_id=result.get("id"),
            file_name=result.get("name"),
            web_view_link=result.get("webViewLink"),
        )

    except Exception as e:
        logger.error(f"Rename failed: {e}")
        return FileOperationResult(
            success=False,
            error=str(e),
        )


def move_file(
    file_id: str,
    new_parent_id: str,
    remove_from_current: bool = True,
) -> FileOperationResult:
    """Move a file or folder to a new parent.

    Args:
        file_id: ID of the file or folder to move.
        new_parent_id: ID of the new parent folder.
        remove_from_current: Remove from current parent(s).

    Returns:
        FileOperationResult: Result of the operation.
    """
    try:
        service = get_drive_service()

        # Get current parents
        file_info = service.files().get(
            fileId=file_id,
            fields="parents",
            supportsAllDrives=True,
        ).execute()

        current_parents = ",".join(file_info.get("parents", []))

        result = service.files().update(
            fileId=file_id,
            addParents=new_parent_id,
            removeParents=current_parents if remove_from_current else None,
            supportsAllDrives=True,
            fields="id, name, webViewLink"
        ).execute()

        return FileOperationResult(
            success=True,
            file_id=result.get("id"),
            file_name=result.get("name"),
            web_view_link=result.get("webViewLink"),
        )

    except Exception as e:
        logger.error(f"Move failed: {e}")
        return FileOperationResult(
            success=False,
            error=str(e),
        )


def get_file_info(file_id: str) -> Optional[DriveFile]:
    """Get information about a file or folder.

    Args:
        file_id: ID of the file or folder.

    Returns:
        DriveFile if found, None otherwise.
    """
    try:
        service = get_drive_service()

        result = service.files().get(
            fileId=file_id,
            supportsAllDrives=True,
            fields="id, name, mimeType, webViewLink, parents, driveId"
        ).execute()

        return DriveFile(
            id=result.get("id", ""),
            name=result.get("name", ""),
            mime_type=result.get("mimeType", ""),
            web_view_link=result.get("webViewLink"),
            parents=result.get("parents", []),
            drive_id=result.get("driveId"),
        )

    except Exception as e:
        logger.error(f"Get file info failed: {e}")
        return None


def get_user_info() -> dict:
    """Get information about the authenticated user.

    Returns:
        dict: User information including email and storage quota.
    """
    try:
        service = get_drive_service()

        about = service.about().get(
            fields="user, storageQuota"
        ).execute()

        return {
            "success": True,
            "email": about.get("user", {}).get("emailAddress"),
            "name": about.get("user", {}).get("displayName"),
            "storage_quota": about.get("storageQuota"),
        }

    except Exception as e:
        logger.error(f"Get user info failed: {e}")
        return {
            "success": False,
            "error": str(e),
        }
