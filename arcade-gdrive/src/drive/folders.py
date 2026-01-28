"""
Google Drive folder operations.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from ..auth import get_drive_service, GoogleAuthError
from .utils import build_drive_url, validate_folder_name, validate_file_id

logger = logging.getLogger(__name__)


@dataclass
class FolderResult:
    """Result of a folder operation."""

    success: bool
    folder_id: Optional[str]
    folder_url: Optional[str]
    message: str


def create_folder(
    name: str,
    parent_id: Optional[str] = None,
    description: Optional[str] = None,
    shared_drive_id: Optional[str] = None,
) -> FolderResult:
    """Create a new folder in Google Drive.

    Args:
        name: Name for the new folder.
        parent_id: Optional parent folder ID. If not provided, creates in root.
        description: Optional description for the folder.
        shared_drive_id: Optional Shared Drive ID if creating in a Shared Drive.

    Returns:
        FolderResult: Result containing folder ID and URL if successful.
    """
    # Validate inputs
    try:
        name = validate_folder_name(name)
    except ValueError as e:
        return FolderResult(
            success=False,
            folder_id=None,
            folder_url=None,
            message=str(e),
        )

    if parent_id:
        try:
            parent_id = validate_file_id(parent_id, "parent_id")
        except ValueError as e:
            return FolderResult(
                success=False,
                folder_id=None,
                folder_url=None,
                message=str(e),
            )

    try:
        service = get_drive_service()

        # Build file metadata
        file_metadata = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
        }

        if parent_id:
            file_metadata["parents"] = [parent_id]

        if description:
            file_metadata["description"] = description

        # Create the folder
        result = service.files().create(
            body=file_metadata,
            supportsAllDrives=True,
            fields="id, name, webViewLink"
        ).execute()

        folder_id = result.get("id")

        # Critical fix: Don't return success=True if folder_id is None
        if not folder_id:
            logger.error(f"API returned success but no folder ID: {result}")
            return FolderResult(
                success=False,
                folder_id=None,
                folder_url=None,
                message="API response missing folder ID",
            )

        folder_url = result.get("webViewLink") or build_drive_url(folder_id, is_folder=True)

        return FolderResult(
            success=True,
            folder_id=folder_id,
            folder_url=folder_url,
            message=f"Created folder '{name}'",
        )

    except GoogleAuthError as e:
        logger.error(f"Create folder failed: {e}")
        return FolderResult(
            success=False,
            folder_id=None,
            folder_url=None,
            message=str(e),
        )
    except Exception as e:
        logger.error(f"Create folder failed: {e}")
        return FolderResult(
            success=False,
            folder_id=None,
            folder_url=None,
            message=str(e),
        )


def create_nested_folders(
    path: str,
    root_parent_id: Optional[str] = None,
) -> FolderResult:
    """Create nested folders from a path string.

    Creates each folder in the path if it doesn't exist.

    Args:
        path: Path like "parent/child/grandchild".
        root_parent_id: Optional ID of the root parent folder.

    Returns:
        FolderResult: Result containing the deepest folder's ID and URL.
    """
    if not path or not isinstance(path, str):
        return FolderResult(
            success=False,
            folder_id=None,
            folder_url=None,
            message="Path must be a non-empty string",
        )

    # Split path and filter empty parts
    parts = [p.strip() for p in path.split("/") if p.strip()]

    if not parts:
        return FolderResult(
            success=False,
            folder_id=None,
            folder_url=None,
            message="Path contains no valid folder names",
        )

    current_parent_id = root_parent_id
    last_result: Optional[FolderResult] = None

    for folder_name in parts:
        result = create_folder(folder_name, parent_id=current_parent_id)

        if not result.success:
            # Include context about where in the path we failed
            return FolderResult(
                success=False,
                folder_id=None,
                folder_url=None,
                message=f"Failed to create '{folder_name}': {result.message}",
            )

        current_parent_id = result.folder_id
        last_result = result

    # Return the last created folder
    if last_result:
        return last_result

    return FolderResult(
        success=False,
        folder_id=None,
        folder_url=None,
        message="No folders were created",
    )


def move_to_folder(
    file_id: str,
    new_parent_id: str,
    remove_from_current: bool = True,
    new_filename: Optional[str] = None,
) -> FolderResult:
    """Move a file or folder to a new parent folder.

    Args:
        file_id: ID of the file or folder to move.
        new_parent_id: ID of the destination folder.
        remove_from_current: If True, remove from current parent(s).
        new_filename: Optional new name for the file after moving (rename while moving).

    Returns:
        FolderResult: Result of the operation.
    """
    try:
        file_id = validate_file_id(file_id, "file_id")
        new_parent_id = validate_file_id(new_parent_id, "new_parent_id")
    except ValueError as e:
        return FolderResult(
            success=False,
            folder_id=None,
            folder_url=None,
            message=str(e),
        )

    try:
        service = get_drive_service()

        # Get current parents
        file_info = service.files().get(
            fileId=file_id,
            fields="parents",
            supportsAllDrives=True,
        ).execute()

        current_parents = ",".join(file_info.get("parents", []))

        # Build update body
        body = {}
        if new_filename:
            body["name"] = new_filename

        # Move the file
        result = service.files().update(
            fileId=file_id,
            body=body if body else None,
            addParents=new_parent_id,
            removeParents=current_parents if remove_from_current else None,
            supportsAllDrives=True,
            fields="id, name, webViewLink"
        ).execute()

        return FolderResult(
            success=True,
            folder_id=file_id,
            folder_url=build_drive_url(file_id, is_folder=True),
            message=f"Moved item to folder {new_parent_id}",
        )

    except GoogleAuthError as e:
        logger.error(f"Move to folder failed: {e}")
        return FolderResult(
            success=False,
            folder_id=None,
            folder_url=None,
            message=str(e),
        )
    except Exception as e:
        logger.error(f"Move to folder failed: {e}")
        return FolderResult(
            success=False,
            folder_id=None,
            folder_url=None,
            message=str(e),
        )
