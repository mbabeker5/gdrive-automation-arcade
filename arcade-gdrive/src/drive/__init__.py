"""
Google Drive operations module.

Provides functions for searching, creating folders, sharing, and downloading
files from Google Drive using Arcade.
"""

from .download import download_file, download_to_memory, DownloadResult
from .files import rename_file, upload_file, FileResult, UploadResult
from .folders import create_folder, create_nested_folders, move_to_folder, FolderResult
from .search import (
    search,
    find_by_name,
    find_by_id,
    get_url_by_id,
    list_shared_drives,
    get_file_tree_structure,
    get_user_info,
    generate_file_picker_url,
    SearchResult,
    FileInfo,
    TreeNode,
    TreeResult,
    UserInfo,
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
from .google_api import (
    search_all,
    list_folder_contents,
    create_folder_in_shared_drive,
    delete_file,
    get_shared_drives,
    SearchAllResult,
    ListContentsResult,
    FolderCreateResult,
    DriveFile,
)

__all__ = [
    # Download
    "download_file",
    "download_to_memory",
    "DownloadResult",
    # Files
    "rename_file",
    "upload_file",
    "FileResult",
    "UploadResult",
    # Folders
    "create_folder",
    "create_nested_folders",
    "move_to_folder",
    "FolderResult",
    # Search
    "search",
    "find_by_name",
    "find_by_id",
    "get_url_by_id",
    "list_shared_drives",
    "get_file_tree_structure",
    "get_user_info",
    "generate_file_picker_url",
    "SearchResult",
    "FileInfo",
    "TreeNode",
    "TreeResult",
    "UserInfo",
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
    # Google API (full Drive access)
    "search_all",
    "list_folder_contents",
    "create_folder_in_shared_drive",
    "delete_file",
    "get_shared_drives",
    "SearchAllResult",
    "ListContentsResult",
    "FolderCreateResult",
    "DriveFile",
]
