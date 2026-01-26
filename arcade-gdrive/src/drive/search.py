"""
Google Drive search operations.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from ..auth import execute_tool, ArcadeToolError
from .utils import build_drive_url, is_folder as check_is_folder, validate_file_id

logger = logging.getLogger(__name__)


@dataclass
class FileInfo:
    """Information about a Google Drive file or folder."""

    id: str
    name: str
    mime_type: str
    url: str
    is_folder: bool
    parent_id: Optional[str] = None
    size: Optional[int] = None
    created_time: Optional[str] = None
    modified_time: Optional[str] = None

    @classmethod
    def from_api_response(cls, data: dict, assume_folder: Optional[bool] = None) -> "FileInfo":
        """Create a FileInfo from an API response dictionary.

        Args:
            data: Dictionary from the API response.
            assume_folder: If provided, use this instead of detecting folder status.

        Returns:
            FileInfo: Populated file info object.
        """
        file_id = data.get("id", "")
        item_is_folder = check_is_folder(data, assume_folder=assume_folder)

        # Prefer webViewLink from API, fall back to constructed URL
        url = data.get("webViewLink") or build_drive_url(file_id, is_folder=item_is_folder)

        return cls(
            id=file_id,
            name=data.get("name", ""),
            mime_type=data.get("mimeType", ""),
            url=url,
            is_folder=item_is_folder,
            parent_id=data.get("parents", [None])[0] if data.get("parents") else None,
            size=data.get("size"),
            created_time=data.get("createdTime"),
            modified_time=data.get("modifiedTime"),
        )


@dataclass
class SearchResult:
    """Result of a search operation."""

    success: bool
    files: list[FileInfo]
    total_count: int
    message: str = ""


def search(
    query: str,
    max_results: int = 100,
    file_type: Optional[str] = None,
    parent_id: Optional[str] = None,
) -> SearchResult:
    """Search for files and folders in Google Drive.

    Args:
        query: Search query string.
        max_results: Maximum number of results to return.
        file_type: Optional filter for file type (e.g., "folder", "document").
        parent_id: Optional parent folder ID to search within.

    Returns:
        SearchResult: The search results.
    """
    if not query or not isinstance(query, str):
        return SearchResult(
            success=False,
            files=[],
            total_count=0,
            message="Query must be a non-empty string",
        )

    try:
        # Build search parameters
        params = {
            "query": query,
            "limit": min(max_results, 1000),  # API limit
        }

        if file_type:
            params["file_types"] = [file_type]

        if parent_id:
            params["folder_path_or_id"] = parent_id

        result = execute_tool("GoogleDrive.SearchFiles", **params)

        # Handle various response formats
        files_data = []
        if isinstance(result, dict):
            files_data = result.get("files", [])
        elif isinstance(result, list):
            files_data = result

        files = [FileInfo.from_api_response(f) for f in files_data]

        return SearchResult(
            success=True,
            files=files,
            total_count=len(files),
            message=f"Found {len(files)} result(s)",
        )

    except ArcadeToolError as e:
        logger.error(f"Search failed: {e}")
        return SearchResult(
            success=False,
            files=[],
            total_count=0,
            message=str(e),
        )


def find_by_name(
    name: str,
    exact_match: bool = True,
    file_type: Optional[str] = None,
    parent_id: Optional[str] = None,
) -> SearchResult:
    """Find files or folders by name.

    Args:
        name: The name to search for.
        exact_match: If True, only return exact name matches.
        file_type: Optional filter for file type.
        parent_id: Optional parent folder ID to search within.

    Returns:
        SearchResult: The search results.
    """
    if not name or not isinstance(name, str):
        return SearchResult(
            success=False,
            files=[],
            total_count=0,
            message="Name must be a non-empty string",
        )

    result = search(name, file_type=file_type, parent_id=parent_id)

    if not result.success:
        return result

    if exact_match:
        # Filter to exact matches
        exact_files = [f for f in result.files if f.name == name]
        return SearchResult(
            success=True,
            files=exact_files,
            total_count=len(exact_files),
            message=f"Found {len(exact_files)} exact match(es)",
        )

    return result


def find_by_id(
    file_id: str,
    assume_folder: Optional[bool] = None,
) -> Optional[FileInfo]:
    """Find a file or folder by its ID.

    IMPORTANT: This function has limitations. The Google.SearchFiles API
    may not reliably find items by ID, especially for items in Shared Drives
    or items with restricted access. If you just need the URL and already
    have the ID, use `get_url_by_id()` instead which constructs the URL directly.

    Args:
        file_id: The Google Drive file or folder ID.
        assume_folder: If True, assume the ID is a folder when constructing URLs.
            If None, will try to detect from API response.

    Returns:
        FileInfo if found, None otherwise.
    """
    try:
        file_id = validate_file_id(file_id)
    except ValueError as e:
        logger.error(f"Invalid file ID: {e}")
        return None

    try:
        result = execute_tool("GoogleDrive.SearchFiles", query=file_id)

        # Handle various response formats
        files_data = []
        if isinstance(result, dict):
            files_data = result.get("files", [])
        elif isinstance(result, list):
            files_data = result

        # Find the matching file
        for f in files_data:
            if f.get("id") == file_id:
                return FileInfo.from_api_response(f, assume_folder=assume_folder)

        # Not found via search - this is a known limitation
        logger.warning(
            f"File ID {file_id} not found via search. "
            "Consider using get_url_by_id() if you just need the URL."
        )
        return None

    except ArcadeToolError as e:
        logger.error(f"Find by ID failed: {e}")
        return None


def get_url_by_id(file_id: str, is_folder: bool = False) -> str:
    """Get the Google Drive URL for a file or folder ID.

    This is a reliable alternative to find_by_id() when you just need
    the URL and already have the ID. It constructs the URL directly
    without making any API calls.

    Args:
        file_id: The Google Drive file or folder ID.
        is_folder: True if the ID is for a folder, False for a file.

    Returns:
        str: The Google Drive URL.

    Raises:
        ValueError: If file_id is invalid.
    """
    file_id = validate_file_id(file_id)
    return build_drive_url(file_id, is_folder=is_folder)


def list_shared_drives() -> SearchResult:
    """List all Shared Drives accessible to the user.

    Uses GoogleDrive.WhoAmI which includes shared drives in its response.

    Returns:
        SearchResult: List of Shared Drives as FileInfo objects.
    """
    try:
        result = execute_tool("GoogleDrive.WhoAmI")

        # WhoAmI returns user info with sharedDrives list
        drives_data = []
        if isinstance(result, dict):
            drives_data = result.get("sharedDrives", result.get("shared_drives", []))

        drives = []
        for d in drives_data:
            drive_id = d.get("id", "")
            drives.append(
                FileInfo(
                    id=drive_id,
                    name=d.get("name", ""),
                    mime_type="application/vnd.google-apps.folder",
                    url=build_drive_url(drive_id, is_folder=True) if drive_id else "",
                    is_folder=True,
                )
            )

        return SearchResult(
            success=True,
            files=drives,
            total_count=len(drives),
            message=f"Found {len(drives)} Shared Drive(s)",
        )

    except ArcadeToolError as e:
        logger.error(f"List shared drives failed: {e}")
        return SearchResult(
            success=False,
            files=[],
            total_count=0,
            message=str(e),
        )
