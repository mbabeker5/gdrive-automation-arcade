"""
Google Drive operations module.

Provides functions for searching, creating folders, sharing, and downloading
files from Google Drive using Arcade.
"""

from .download import download_file, download_to_memory, DownloadResult
from .folders import create_folder, create_nested_folders, FolderResult
from .search import (
    search,
    find_by_name,
    find_by_id,
    get_url_by_id,
    list_shared_drives,
    SearchResult,
    FileInfo,
)
from .sharing import (
    share_with_users,
    create_folder_and_share,
    create_folder_and_get_url,
    ShareResult,
    UrlResult,
)
from .utils import (
    build_drive_url,
    parse_file_id,
    is_folder,
    DRIVE_FILE_URL_TEMPLATE,
    DRIVE_FOLDER_URL_TEMPLATE,
)

__all__ = [
    # Download
    "download_file",
    "download_to_memory",
    "DownloadResult",
    # Folders
    "create_folder",
    "create_nested_folders",
    "FolderResult",
    # Search
    "search",
    "find_by_name",
    "find_by_id",
    "get_url_by_id",
    "list_shared_drives",
    "SearchResult",
    "FileInfo",
    # Sharing
    "share_with_users",
    "create_folder_and_share",
    "create_folder_and_get_url",
    "ShareResult",
    "UrlResult",
    # Utils
    "build_drive_url",
    "parse_file_id",
    "is_folder",
    "DRIVE_FILE_URL_TEMPLATE",
    "DRIVE_FOLDER_URL_TEMPLATE",
]
