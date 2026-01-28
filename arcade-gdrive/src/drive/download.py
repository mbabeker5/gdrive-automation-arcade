"""
Google Drive file download operations.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from googleapiclient.http import MediaIoBaseDownload

from ..auth import get_drive_service, GoogleAuthError
from .utils import validate_file_id

logger = logging.getLogger(__name__)

# Default chunk size in bytes (1 MB)
DEFAULT_CHUNK_SIZE = 1024 * 1024


@dataclass
class DownloadResult:
    """Result of a download operation."""

    success: bool
    message: str
    file_path: Optional[Path] = None
    file_size: Optional[int] = None
    chunks_downloaded: int = 0


def download_file(
    file_id: str,
    output_path: str | Path,
) -> DownloadResult:
    """Download a file from Google Drive.

    Downloads the file using Google's MediaIoBaseDownload for reliable
    chunked transfers.

    Args:
        file_id: The ID of the file to download.
        output_path: Local path where the file should be saved.

    Returns:
        DownloadResult: Result of the download operation.
    """
    # Validate inputs
    try:
        file_id = validate_file_id(file_id)
    except ValueError as e:
        return DownloadResult(success=False, message=str(e))

    if not output_path:
        return DownloadResult(
            success=False,
            message="output_path must be specified",
        )

    output_path = Path(output_path)

    # Ensure parent directory exists
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return DownloadResult(
            success=False,
            message=f"Cannot create output directory: {e}",
        )

    try:
        service = get_drive_service()

        # Get file metadata first
        file_metadata = service.files().get(
            fileId=file_id,
            supportsAllDrives=True,
            fields="name, mimeType, size"
        ).execute()

        mime_type = file_metadata.get("mimeType", "")

        # Handle Google Docs/Sheets/Slides - must be exported
        export_mime_types = {
            "application/vnd.google-apps.document": "application/pdf",
            "application/vnd.google-apps.spreadsheet": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.google-apps.presentation": "application/pdf",
            "application/vnd.google-apps.drawing": "image/png",
        }

        if mime_type in export_mime_types:
            # Export Google Workspace file
            request = service.files().export_media(
                fileId=file_id,
                mimeType=export_mime_types[mime_type]
            )
        else:
            # Download binary file
            request = service.files().get_media(
                fileId=file_id,
                supportsAllDrives=True
            )

        # Download with progress tracking
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request, chunksize=DEFAULT_CHUNK_SIZE)

        done = False
        chunks_downloaded = 0
        while not done:
            status, done = downloader.next_chunk()
            chunks_downloaded += 1
            if status:
                logger.debug(f"Download progress: {int(status.progress() * 100)}%")

        # Write to file
        fh.seek(0)
        with open(output_path, "wb") as f:
            f.write(fh.read())

        file_size = output_path.stat().st_size

        return DownloadResult(
            success=True,
            message=f"Downloaded {file_size} bytes in {chunks_downloaded} chunk(s)",
            file_path=output_path,
            file_size=file_size,
            chunks_downloaded=chunks_downloaded,
        )

    except GoogleAuthError as e:
        _cleanup_partial_file(output_path)
        return DownloadResult(
            success=False,
            message=str(e),
        )
    except OSError as e:
        _cleanup_partial_file(output_path)
        return DownloadResult(
            success=False,
            message=f"File system error: {e}",
        )
    except Exception as e:
        logger.error(f"Unexpected error during download: {e}")
        _cleanup_partial_file(output_path)
        return DownloadResult(
            success=False,
            message=f"Unexpected error: {e}",
        )


def _cleanup_partial_file(path: Path) -> None:
    """Remove a partial file after a failed download.

    Args:
        path: Path to the file to remove.
    """
    try:
        if path.exists():
            path.unlink()
            logger.debug(f"Cleaned up partial file: {path}")
    except OSError as e:
        logger.warning(f"Could not clean up partial file {path}: {e}")


def download_to_memory(
    file_id: str,
    max_size_mb: int = 100,
) -> tuple[bool, bytes | str]:
    """Download a file to memory instead of disk.

    Use with caution for larger files as this loads the entire
    file into memory.

    Args:
        file_id: The ID of the file to download.
        max_size_mb: Maximum file size in MB to download.

    Returns:
        tuple: (success: bool, data: bytes | error_message: str)
    """
    try:
        file_id = validate_file_id(file_id)
    except ValueError as e:
        return False, str(e)

    max_size_bytes = max_size_mb * 1024 * 1024

    try:
        service = get_drive_service()

        # Check file size first
        file_metadata = service.files().get(
            fileId=file_id,
            supportsAllDrives=True,
            fields="size, mimeType"
        ).execute()

        file_size = file_metadata.get("size")
        if file_size and int(file_size) > max_size_bytes:
            return False, f"File exceeds maximum size of {max_size_mb} MB"

        mime_type = file_metadata.get("mimeType", "")

        # Handle Google Workspace files
        export_mime_types = {
            "application/vnd.google-apps.document": "application/pdf",
            "application/vnd.google-apps.spreadsheet": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.google-apps.presentation": "application/pdf",
            "application/vnd.google-apps.drawing": "image/png",
        }

        if mime_type in export_mime_types:
            request = service.files().export_media(
                fileId=file_id,
                mimeType=export_mime_types[mime_type]
            )
        else:
            request = service.files().get_media(
                fileId=file_id,
                supportsAllDrives=True
            )

        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request, chunksize=DEFAULT_CHUNK_SIZE)

        done = False
        while not done:
            _, done = downloader.next_chunk()

        fh.seek(0)
        data = fh.read()

        if len(data) > max_size_bytes:
            return False, f"File exceeds maximum size of {max_size_mb} MB"

        return True, data

    except GoogleAuthError as e:
        return False, str(e)
    except Exception as e:
        logger.error(f"Download to memory failed: {e}")
        return False, str(e)


def get_download_url(file_id: str) -> tuple[bool, str]:
    """Get a direct download URL for a file.

    Args:
        file_id: The ID of the file.

    Returns:
        tuple: (success: bool, url_or_error: str)
    """
    try:
        file_id = validate_file_id(file_id)
    except ValueError as e:
        return False, str(e)

    return True, f"https://drive.google.com/uc?export=download&id={file_id}"
