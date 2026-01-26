"""
Utility functions for Google Drive operations.
"""

import re
from typing import Optional
from urllib.parse import urlparse, parse_qs

# URL templates for constructing Drive links
DRIVE_FILE_URL_TEMPLATE = "https://drive.google.com/file/d/{file_id}/view"
DRIVE_FOLDER_URL_TEMPLATE = "https://drive.google.com/drive/folders/{folder_id}"


def build_drive_url(file_id: str, is_folder: bool = False) -> str:
    """Build a Google Drive URL from a file/folder ID.

    This is a reliable way to get a Drive URL without API calls.

    Args:
        file_id: The Google Drive file or folder ID.
        is_folder: True if the ID is for a folder, False for a file.

    Returns:
        str: The Google Drive URL.

    Raises:
        ValueError: If file_id is empty or invalid.
    """
    if not file_id or not isinstance(file_id, str):
        raise ValueError("file_id must be a non-empty string")

    file_id = file_id.strip()
    if not file_id:
        raise ValueError("file_id cannot be empty or whitespace")

    if is_folder:
        return DRIVE_FOLDER_URL_TEMPLATE.format(folder_id=file_id)
    return DRIVE_FILE_URL_TEMPLATE.format(file_id=file_id)


def parse_file_id(url_or_id: str) -> str:
    """Extract a file ID from a Google Drive URL or return the ID if already an ID.

    Supports various Google Drive URL formats:
    - https://drive.google.com/file/d/{id}/view
    - https://drive.google.com/open?id={id}
    - https://drive.google.com/drive/folders/{id}
    - https://docs.google.com/document/d/{id}/edit
    - Plain file ID

    Args:
        url_or_id: A Google Drive URL or file ID.

    Returns:
        str: The extracted file ID.

    Raises:
        ValueError: If the input is empty or the ID cannot be extracted.
    """
    if not url_or_id or not isinstance(url_or_id, str):
        raise ValueError("url_or_id must be a non-empty string")

    url_or_id = url_or_id.strip()
    if not url_or_id:
        raise ValueError("url_or_id cannot be empty or whitespace")

    # If it doesn't look like a URL, assume it's already an ID
    if not url_or_id.startswith(("http://", "https://")):
        # Basic validation: Drive IDs are typically alphanumeric with - and _
        if re.match(r"^[\w-]+$", url_or_id):
            return url_or_id
        raise ValueError(f"Invalid file ID format: {url_or_id}")

    parsed = urlparse(url_or_id)

    # Check for ?id= parameter
    query_params = parse_qs(parsed.query)
    if "id" in query_params:
        return query_params["id"][0]

    # Check for /d/{id}/ pattern (files, docs, sheets, etc.)
    d_match = re.search(r"/d/([^/]+)", parsed.path)
    if d_match:
        return d_match.group(1)

    # Check for /folders/{id} pattern
    folders_match = re.search(r"/folders/([^/?]+)", parsed.path)
    if folders_match:
        return folders_match.group(1)

    raise ValueError(f"Could not extract file ID from URL: {url_or_id}")


def is_folder(
    file_info: dict,
    assume_folder: Optional[bool] = None,
) -> bool:
    """Determine if a file info dict represents a folder.

    Args:
        file_info: Dictionary containing file metadata.
        assume_folder: If provided, use this value instead of trying to detect.
            Use this when you know the type to avoid unreliable heuristics.

    Returns:
        bool: True if the item is a folder, False otherwise.
    """
    # If caller explicitly specifies, trust them
    if assume_folder is not None:
        return assume_folder

    # Check MIME type (most reliable)
    mime_type = file_info.get("mimeType", "")
    if mime_type == "application/vnd.google-apps.folder":
        return True

    # Check explicit type field if present
    file_type = file_info.get("type", "").lower()
    if file_type == "folder":
        return True

    # Check kind field (from Drive API v3)
    kind = file_info.get("kind", "")
    if "folder" in kind.lower():
        return True

    # Default to False - we no longer use the fragile dot-based heuristic
    # that assumed files without dots are folders
    return False


def validate_file_id(file_id: str, param_name: str = "file_id") -> str:
    """Validate that a file ID is non-empty and properly formatted.

    Args:
        file_id: The file ID to validate.
        param_name: Name of the parameter for error messages.

    Returns:
        str: The validated and stripped file ID.

    Raises:
        ValueError: If the file ID is invalid.
    """
    if not file_id or not isinstance(file_id, str):
        raise ValueError(f"{param_name} must be a non-empty string")

    file_id = file_id.strip()
    if not file_id:
        raise ValueError(f"{param_name} cannot be empty or whitespace")

    return file_id


def validate_folder_name(name: str) -> str:
    """Validate that a folder name is valid for Google Drive.

    Args:
        name: The folder name to validate.

    Returns:
        str: The validated and stripped folder name.

    Raises:
        ValueError: If the folder name is invalid.
    """
    if not name or not isinstance(name, str):
        raise ValueError("Folder name must be a non-empty string")

    name = name.strip()
    if not name:
        raise ValueError("Folder name cannot be empty or whitespace")

    # Google Drive doesn't allow these characters in names
    invalid_chars = ["\\", "/", ":", "*", "?", '"', "<", ">", "|"]
    for char in invalid_chars:
        if char in name:
            raise ValueError(
                f"Folder name cannot contain '{char}'. "
                f"Invalid characters: {', '.join(invalid_chars)}"
            )

    return name
