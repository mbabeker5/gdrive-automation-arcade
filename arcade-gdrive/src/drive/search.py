"""
Google Drive search operations.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from ..auth import get_drive_service, GoogleAuthError
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
    include_shared_drives: bool = True,
    shared_drive_id: Optional[str] = None,
    include_organization_domain_documents: bool = False,
    order_by: Optional[str] = None,
) -> SearchResult:
    """Search for files and folders in Google Drive.

    Args:
        query: Search query string.
        max_results: Maximum number of results to return.
        file_type: Optional filter for file type (e.g., "folder", "document").
        parent_id: Optional parent folder ID to search within.
        include_shared_drives: Include files from Shared Drives.
        shared_drive_id: Limit search to a specific Shared Drive.
        include_organization_domain_documents: Include organization domain documents.
        order_by: Ordering for results (e.g., "name", "modifiedTime").

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
        service = get_drive_service()

        # Build query parts
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

        # Build request parameters
        params = {
            "q": q,
            "pageSize": min(max_results, 1000),
            "fields": "files(id, name, mimeType, webViewLink, parents, size, createdTime, modifiedTime)",
            "includeItemsFromAllDrives": include_shared_drives,
            "supportsAllDrives": include_shared_drives,
        }

        if shared_drive_id:
            params["corpora"] = "drive"
            params["driveId"] = shared_drive_id

        if order_by:
            params["orderBy"] = order_by

        results = service.files().list(**params).execute()

        files = [FileInfo.from_api_response(f) for f in results.get("files", [])]

        return SearchResult(
            success=True,
            files=files,
            total_count=len(files),
            message=f"Found {len(files)} result(s)",
        )

    except GoogleAuthError as e:
        logger.error(f"Search failed: {e}")
        return SearchResult(
            success=False,
            files=[],
            total_count=0,
            message=str(e),
        )
    except Exception as e:
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
        service = get_drive_service()

        result = service.files().get(
            fileId=file_id,
            supportsAllDrives=True,
            fields="id, name, mimeType, webViewLink, parents, size, createdTime, modifiedTime"
        ).execute()

        return FileInfo.from_api_response(result, assume_folder=assume_folder)

    except Exception as e:
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

    Returns:
        SearchResult: List of Shared Drives as FileInfo objects.
    """
    try:
        service = get_drive_service()

        results = service.drives().list(
            pageSize=100,
            fields="drives(id, name)"
        ).execute()

        drives = []
        for d in results.get("drives", []):
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

    except Exception as e:
        logger.error(f"List shared drives failed: {e}")
        return SearchResult(
            success=False,
            files=[],
            total_count=0,
            message=str(e),
        )


@dataclass
class TreeNode:
    """Represents a node in the file/folder tree structure."""

    id: str
    name: str
    mime_type: str
    is_folder: bool
    children: list["TreeNode"] = field(default_factory=list)


@dataclass
class TreeResult:
    """Result of a get file tree structure operation."""

    success: bool
    root: Optional[TreeNode]
    total_items: int
    message: str


@dataclass
class UserInfo:
    """Information about the authenticated user and Drive environment."""

    success: bool
    email: Optional[str]
    name: Optional[str]
    shared_drives: list[FileInfo]
    raw_response: dict
    message: str


def get_file_tree_structure(
    include_shared_drives: bool = False,
    restrict_to_shared_drive_id: Optional[str] = None,
    include_organization_domain_documents: bool = False,
    order_by: Optional[str] = None,
    limit: Optional[int] = 100,
) -> TreeResult:
    """Get the file/folder tree structure from Google Drive.

    WARNING: This can be inefficient for large drives. Use the limit parameter
    to restrict the number of items returned.

    Args:
        include_shared_drives: Include files from Shared Drives.
        restrict_to_shared_drive_id: Limit to a specific Shared Drive.
        include_organization_domain_documents: Include organization domain documents.
        order_by: Ordering for results (e.g., "name", "modifiedTime").
        limit: Maximum number of items to return (default 100).

    Returns:
        TreeResult: The file tree structure.
    """
    try:
        service = get_drive_service()

        params = {
            "pageSize": min(limit or 100, 1000),
            "fields": "files(id, name, mimeType, parents)",
            "includeItemsFromAllDrives": include_shared_drives,
            "supportsAllDrives": include_shared_drives,
            "q": "trashed = false",
        }

        if restrict_to_shared_drive_id:
            params["corpora"] = "drive"
            params["driveId"] = restrict_to_shared_drive_id

        if order_by:
            params["orderBy"] = order_by

        results = service.files().list(**params).execute()
        files_data = results.get("files", [])

        # Build tree structure
        nodes_by_id = {}
        root_nodes = []

        for f in files_data:
            node = TreeNode(
                id=f.get("id", ""),
                name=f.get("name", ""),
                mime_type=f.get("mimeType", ""),
                is_folder=f.get("mimeType") == "application/vnd.google-apps.folder",
            )
            nodes_by_id[node.id] = node

        # Link children to parents
        for f in files_data:
            node = nodes_by_id.get(f.get("id"))
            parents = f.get("parents", [])
            if parents:
                parent_id = parents[0]
                if parent_id in nodes_by_id:
                    nodes_by_id[parent_id].children.append(node)
                else:
                    root_nodes.append(node)
            else:
                root_nodes.append(node)

        # Create virtual root
        root = TreeNode(
            id="root",
            name="Root",
            mime_type="application/vnd.google-apps.folder",
            is_folder=True,
            children=root_nodes,
        )

        def count_nodes(node: TreeNode) -> int:
            return 1 + sum(count_nodes(c) for c in node.children)

        total_items = count_nodes(root)

        return TreeResult(
            success=True,
            root=root,
            total_items=total_items,
            message=f"Retrieved tree with {total_items} item(s)",
        )

    except Exception as e:
        logger.error(f"Get file tree structure failed: {e}")
        return TreeResult(
            success=False,
            root=None,
            total_items=0,
            message=str(e),
        )


def get_user_info() -> UserInfo:
    """Get full user profile and Drive environment information.

    Returns:
        UserInfo: Full user information including email, name, and shared drives.
    """
    try:
        service = get_drive_service()

        about = service.about().get(
            fields="user, storageQuota"
        ).execute()

        # Get shared drives separately
        drives_result = list_shared_drives()

        return UserInfo(
            success=True,
            email=about.get("user", {}).get("emailAddress"),
            name=about.get("user", {}).get("displayName"),
            shared_drives=drives_result.files if drives_result.success else [],
            raw_response=about,
            message="User info retrieved successfully",
        )

    except Exception as e:
        logger.error(f"Get user info failed: {e}")
        return UserInfo(
            success=False,
            email=None,
            name=None,
            shared_drives=[],
            raw_response={},
            message=str(e),
        )


def generate_file_picker_url() -> str:
    """Generate a Google File Picker URL.

    Note: This functionality requires the Google Picker API to be enabled
    and configured in your Google Cloud project.

    Returns:
        str: Information about setting up the File Picker.
    """
    return (
        "To use the Google File Picker, you need to:\n"
        "1. Enable the Google Picker API in your Google Cloud project\n"
        "2. Create an API key with Picker API access\n"
        "3. Implement the Picker in your frontend using the JavaScript API\n"
        "See: https://developers.google.com/drive/picker"
    )
