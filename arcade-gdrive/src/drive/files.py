"""
Google Drive file operations (rename, upload).
"""

import logging
from dataclasses import dataclass
from typing import Optional

from ..auth import get_drive_service, GoogleAuthError
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
        service = get_drive_service()

        result = service.files().update(
            fileId=file_id,
            body={"name": new_name},
            supportsAllDrives=True,
            fields="id, name, webViewLink"
        ).execute()

        result_id = result.get("id", file_id)
        file_url = result.get("webViewLink") or build_drive_url(result_id, is_folder=False)

        return FileResult(
            success=True,
            file_id=result_id,
            file_url=file_url,
            message=f"Renamed to '{new_name}'",
        )

    except GoogleAuthError as e:
        logger.error(f"Rename file failed: {e}")
        return FileResult(
            success=False,
            file_id=None,
            file_url=None,
            message=str(e),
        )
    except Exception as e:
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

    Note: This function requires the file content to be downloaded first.
    For URL-based uploads, consider using the Google Drive API's
    web content link feature or download the file locally first.

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
        import urllib.request
        from googleapiclient.http import MediaInMemoryUpload

        service = get_drive_service()

        # Download the file content
        with urllib.request.urlopen(source_url) as response:
            content = response.read()
            content_type = mime_type or response.headers.get("Content-Type", "application/octet-stream")

        # Build file metadata
        file_metadata = {"name": file_name}
        if destination_folder_id:
            file_metadata["parents"] = [destination_folder_id]

        # Create media upload
        media = MediaInMemoryUpload(content, mimetype=content_type)

        # Upload the file
        result = service.files().create(
            body=file_metadata,
            media_body=media,
            supportsAllDrives=True,
            fields="id, name, webViewLink"
        ).execute()

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

    except GoogleAuthError as e:
        logger.error(f"Upload file failed: {e}")
        return UploadResult(
            success=False,
            file_id=None,
            file_url=None,
            file_name=file_name,
            message=str(e),
        )
    except Exception as e:
        logger.error(f"Upload file failed: {e}")
        return UploadResult(
            success=False,
            file_id=None,
            file_url=None,
            file_name=file_name,
            message=str(e),
        )


def upload_local_file(
    file_path: str,
    file_name: Optional[str] = None,
    mime_type: Optional[str] = None,
    destination_folder_id: Optional[str] = None,
) -> UploadResult:
    """Upload a local file to Google Drive.

    Args:
        file_path: Path to the local file.
        file_name: Optional name for the uploaded file (defaults to filename).
        mime_type: Optional MIME type for the file.
        destination_folder_id: Optional destination folder ID.

    Returns:
        UploadResult: Result containing file ID, URL, and name if successful.
    """
    import os
    from pathlib import Path
    from googleapiclient.http import MediaFileUpload

    file_path = Path(file_path)

    if not file_path.exists():
        return UploadResult(
            success=False,
            file_id=None,
            file_url=None,
            file_name=file_name or "",
            message=f"File not found: {file_path}",
        )

    actual_name = file_name or file_path.name

    try:
        service = get_drive_service()

        # Build file metadata
        file_metadata = {"name": actual_name}
        if destination_folder_id:
            file_metadata["parents"] = [destination_folder_id]

        # Create media upload
        media = MediaFileUpload(
            str(file_path),
            mimetype=mime_type,
            resumable=True
        )

        # Upload the file
        result = service.files().create(
            body=file_metadata,
            media_body=media,
            supportsAllDrives=True,
            fields="id, name, webViewLink"
        ).execute()

        result_id = result.get("id")
        if not result_id:
            return UploadResult(
                success=False,
                file_id=None,
                file_url=None,
                file_name=actual_name,
                message="API response missing file ID",
            )

        file_url = result.get("webViewLink") or build_drive_url(result_id, is_folder=False)

        return UploadResult(
            success=True,
            file_id=result_id,
            file_url=file_url,
            file_name=result.get("name", actual_name),
            message=f"Uploaded '{actual_name}'",
        )

    except Exception as e:
        logger.error(f"Upload local file failed: {e}")
        return UploadResult(
            success=False,
            file_id=None,
            file_url=None,
            file_name=actual_name,
            message=str(e),
        )
