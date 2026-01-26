"""
Google Drive file download operations.
"""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..auth import execute_tool, ArcadeToolError
from .utils import validate_file_id

logger = logging.getLogger(__name__)

# Safety limit to prevent infinite loops in chunked downloads
DEFAULT_MAX_ITERATIONS = 10000

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
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
) -> DownloadResult:
    """Download a file from Google Drive.

    Downloads the file in chunks to handle large files safely.
    Includes protection against infinite loops.

    Args:
        file_id: The ID of the file to download.
        output_path: Local path where the file should be saved.
        max_iterations: Maximum number of chunks to download (safety limit).

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
        # Start chunked download
        iterations = 0
        total_bytes = 0
        offset = 0

        with open(output_path, "wb") as f:
            while iterations < max_iterations:
                iterations += 1

                try:
                    # Use DownloadFileChunk for chunked downloads with offset
                    if offset > 0:
                        result = execute_tool(
                            "GoogleDrive.DownloadFileChunk",
                            file_path_or_id=file_id,
                            start_byte=offset,
                            chunk_size=DEFAULT_CHUNK_SIZE,
                        )
                    else:
                        # First chunk - use DownloadFile which handles small files directly
                        result = execute_tool(
                            "GoogleDrive.DownloadFile",
                            file_path_or_id=file_id,
                        )
                except ArcadeToolError as e:
                    # Clean up partial file on error
                    _cleanup_partial_file(output_path)
                    return DownloadResult(
                        success=False,
                        message=f"Download failed at chunk {iterations}: {e}",
                        chunks_downloaded=iterations - 1,
                    )

                # Validate response format
                if not isinstance(result, dict):
                    _cleanup_partial_file(output_path)
                    return DownloadResult(
                        success=False,
                        message=f"Unexpected response format at chunk {iterations}",
                        chunks_downloaded=iterations - 1,
                    )

                # Get content - handle various possible keys
                content_b64 = result.get("content") or result.get("data") or result.get("chunk")

                # Critical fix: Check for empty chunk
                if not content_b64:
                    # If this is the first chunk and it's empty, the file might be empty
                    if iterations == 1:
                        # Check if file is intentionally empty
                        if result.get("is_final_chunk") or result.get("done"):
                            logger.info("Downloaded empty file")
                            return DownloadResult(
                                success=True,
                                message="Downloaded empty file",
                                file_path=output_path,
                                file_size=0,
                                chunks_downloaded=1,
                            )

                    _cleanup_partial_file(output_path)
                    return DownloadResult(
                        success=False,
                        message=f"Empty chunk received at iteration {iterations}",
                        chunks_downloaded=iterations - 1,
                    )

                # Decode and write chunk
                try:
                    chunk_data = base64.b64decode(content_b64)
                except Exception as e:
                    _cleanup_partial_file(output_path)
                    return DownloadResult(
                        success=False,
                        message=f"Failed to decode chunk {iterations}: {e}",
                        chunks_downloaded=iterations - 1,
                    )

                f.write(chunk_data)
                chunk_size = len(chunk_data)
                total_bytes += chunk_size
                offset += chunk_size

                logger.debug(f"Downloaded chunk {iterations}: {chunk_size} bytes")

                # Check if download is complete
                if result.get("is_final_chunk") or result.get("done") or result.get("complete"):
                    return DownloadResult(
                        success=True,
                        message=f"Downloaded {total_bytes} bytes in {iterations} chunk(s)",
                        file_path=output_path,
                        file_size=total_bytes,
                        chunks_downloaded=iterations,
                    )

                # Check if we got less than expected (might indicate end of file)
                expected_size = result.get("chunk_size", DEFAULT_CHUNK_SIZE)
                if chunk_size < expected_size:
                    # Likely the last chunk
                    return DownloadResult(
                        success=True,
                        message=f"Downloaded {total_bytes} bytes in {iterations} chunk(s)",
                        file_path=output_path,
                        file_size=total_bytes,
                        chunks_downloaded=iterations,
                    )

        # Critical fix: If we reach here, we hit the iteration limit
        _cleanup_partial_file(output_path)
        return DownloadResult(
            success=False,
            message=(
                f"Download exceeded iteration limit ({max_iterations}). "
                f"Downloaded {total_bytes} bytes in {iterations} chunks before stopping. "
                "File may be very large or API may be returning incorrect chunk status."
            ),
            chunks_downloaded=iterations,
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
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
) -> tuple[bool, bytes | str]:
    """Download a file to memory instead of disk.

    Use with caution for larger files as this loads the entire
    file into memory.

    Args:
        file_id: The ID of the file to download.
        max_size_mb: Maximum file size in MB to download.
        max_iterations: Maximum number of chunks (safety limit).

    Returns:
        tuple: (success: bool, data: bytes | error_message: str)
    """
    try:
        file_id = validate_file_id(file_id)
    except ValueError as e:
        return False, str(e)

    max_size_bytes = max_size_mb * 1024 * 1024
    chunks: list[bytes] = []
    iterations = 0
    total_bytes = 0
    offset = 0

    while iterations < max_iterations:
        iterations += 1

        try:
            # Use DownloadFileChunk for chunked downloads with offset
            if offset > 0:
                result = execute_tool(
                    "GoogleDrive.DownloadFileChunk",
                    file_path_or_id=file_id,
                    start_byte=offset,
                    chunk_size=DEFAULT_CHUNK_SIZE,
                )
            else:
                result = execute_tool(
                    "GoogleDrive.DownloadFile",
                    file_path_or_id=file_id,
                )
        except ArcadeToolError as e:
            return False, f"Download failed at chunk {iterations}: {e}"

        if not isinstance(result, dict):
            return False, f"Unexpected response format at chunk {iterations}"

        content_b64 = result.get("content") or result.get("data") or result.get("chunk")

        if not content_b64:
            if iterations == 1 and (result.get("is_final_chunk") or result.get("done")):
                return True, b""
            return False, f"Empty chunk received at iteration {iterations}"

        try:
            chunk_data = base64.b64decode(content_b64)
        except Exception as e:
            return False, f"Failed to decode chunk {iterations}: {e}"

        total_bytes += len(chunk_data)

        # Check size limit
        if total_bytes > max_size_bytes:
            return False, f"File exceeds maximum size of {max_size_mb} MB"

        chunks.append(chunk_data)
        offset += len(chunk_data)

        if result.get("is_final_chunk") or result.get("done") or result.get("complete"):
            return True, b"".join(chunks)

        expected_size = result.get("chunk_size", DEFAULT_CHUNK_SIZE)
        if len(chunk_data) < expected_size:
            return True, b"".join(chunks)

    return False, f"Download exceeded iteration limit ({max_iterations})"


def get_download_url(file_id: str) -> tuple[bool, str]:
    """Get a direct download URL for a file.

    NOTE: This functionality is not directly available in Arcade's Google Drive toolkit.
    Use download_file() or download_to_memory() instead.

    Args:
        file_id: The ID of the file.

    Returns:
        tuple: (success: bool, url_or_error: str)
    """
    return False, "get_download_url is not available - use download_file() instead"
