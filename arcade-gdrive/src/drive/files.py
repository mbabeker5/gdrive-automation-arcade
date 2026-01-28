"""
Google Drive file operations (rename, upload).
"""

import logging
from dataclasses import dataclass
from typing import Optional

from ..auth import execute_tool, ArcadeToolError
from .utils import build_drive_url, validate_file_id

logger = logging.getLogger(__name__)


@dataclass
class FileResult:
    """Result of a file operation."""

    success: bool
    file_id: Optional[str]
    file_url: Optional[str]
    message: str


@dataclass
class UploadResult:
    """Result of an upload operation."""

    success: bool
    file_id: Optional[str]
    file_url: Optional[str]
    file_name: str
    message: str


def rename_file(
    file_id: str,
    new_name: str,
    shared_drive_id: Optional[str] = None,
) -> FileResult:
    """Rename a file or folder in Google Drive.

    Args:
        file_id: ID of the file or folder to rename.
        new_name: New name for the file or folder.
        shared_drive_id: Optional Shared Drive ID if the file is in a Shared Drive.

    Returns:
        FileResult: Result containing file ID and URL if successful.
    """
    # Validate inputs
    try:
        file_id = validate_file_id(file_id)
    except ValueError as e:
        return FileResult(
            success=False,
            file_id=None,
            file_url=None,
            message=str(e),
        )

    if not new_name or not isinstance(new_name, str):
        return FileResult(
            success=False,
            file_id=None,
            file_url=None,
            message="new_name must be a non-empty string",
        )

    new_name = new_name.strip()
    if not new_name:
        return FileResult(
            success=False,
            file_id=None,
            file_url=None,
            message="new_name cannot be empty or whitespace",
        )

    try:
        # Build parameters for GoogleDrive.RenameFile
        params = {
            "file_path_or_id": file_id,
            "new_filename": new_name,
        }

        if shared_drive_id:
            params["shared_drive_id"] = shared_drive_id

        result = execute_tool("GoogleDrive.RenameFile", **params)

        # Validate response format
        if not isinstance(result, dict):
            logger.error(f"Unexpected response type: {type(result)}")
            return FileResult(
                success=False,
                file_id=None,
                file_url=None,
                message=f"Unexpected response format: expected dict, got {type(result).__name__}",
            )

        result_id = result.get("id", file_id)
        file_url = result.get("webViewLink") or build_drive_url(result_id, is_folder=False)

        return FileResult(
            success=True,
            file_id=result_id,
            file_url=file_url,
            message=f"Renamed to '{new_name}'",
        )

    except ArcadeToolError as e:
        logger.error(f"Rename file failed: {e}")
        return FileResult(
            success=False,
            file_id=None,
            file_url=None,
            message=str(e),
        )


def upload_file(
    file_name: str,
    source_url: str,
    mime_type: Optional[str] = None,
    destination_folder_id: Optional[str] = None,
    shared_drive_id: Optional[str] = None,
) -> UploadResult:
    """Upload a file from a URL to Google Drive.

    Args:
        file_name: Name for the uploaded file.
        source_url: URL to download the file from.
        mime_type: Optional MIME type for the file.
        destination_folder_id: Optional destination folder ID.
        shared_drive_id: Optional Shared Drive ID.

    Returns:
        UploadResult: Result containing file ID, URL, and name if successful.
    """
    # Validate inputs
    if not file_name or not isinstance(file_name, str):
        return UploadResult(
            success=False,
            file_id=None,
            file_url=None,
            file_name="",
            message="file_name must be a non-empty string",
        )

    file_name = file_name.strip()
    if not file_name:
        return UploadResult(
            success=False,
            file_id=None,
            file_url=None,
            file_name="",
            message="file_name cannot be empty or whitespace",
        )

    if not source_url or not isinstance(source_url, str):
        return UploadResult(
            success=False,
            file_id=None,
            file_url=None,
            file_name=file_name,
            message="source_url must be a non-empty string",
        )

    source_url = source_url.strip()
    if not source_url.startswith(("http://", "https://")):
        return UploadResult(
            success=False,
            file_id=None,
            file_url=None,
            file_name=file_name,
            message="source_url must be a valid HTTP/HTTPS URL",
        )

    if destination_folder_id:
        try:
            destination_folder_id = validate_file_id(destination_folder_id, "destination_folder_id")
        except ValueError as e:
            return UploadResult(
                success=False,
                file_id=None,
                file_url=None,
                file_name=file_name,
                message=str(e),
            )

    try:
        # Build parameters for GoogleDrive.UploadFile
        params = {
            "file_name": file_name,
            "source_url": source_url,
        }

        if mime_type:
            params["mime_type"] = mime_type

        if destination_folder_id:
            params["destination_folder_path_or_id"] = destination_folder_id

        if shared_drive_id:
            params["shared_drive_id"] = shared_drive_id

        result = execute_tool("GoogleDrive.UploadFile", **params)

        # Validate response format
        if not isinstance(result, dict):
            logger.error(f"Unexpected response type: {type(result)}")
            return UploadResult(
                success=False,
                file_id=None,
                file_url=None,
                file_name=file_name,
                message=f"Unexpected response format: expected dict, got {type(result).__name__}",
            )

        result_id = result.get("id")
        if not result_id:
            logger.error(f"API returned success but no file ID: {result}")
            return UploadResult(
                success=False,
                file_id=None,
                file_url=None,
                file_name=file_name,
                message="API response missing file ID",
            )

        file_url = result.get("webViewLink") or build_drive_url(result_id, is_folder=False)
        result_name = result.get("name", file_name)

        return UploadResult(
            success=True,
            file_id=result_id,
            file_url=file_url,
            file_name=result_name,
            message=f"Uploaded '{result_name}'",
        )

    except ArcadeToolError as e:
        logger.error(f"Upload file failed: {e}")
        return UploadResult(
            success=False,
            file_id=None,
            file_url=None,
            file_name=file_name,
            message=str(e),
        )
