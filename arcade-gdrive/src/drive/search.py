"""
Google Drive search operations.
"""

import logging
from dataclasses import dataclass, field
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
    include_shared_drives: bool = False,
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
        # Build search parameters
        params = {
            "query": query,
            "limit": min(max_results, 1000),  # API limit
        }

        if file_type:
            params["file_types"] = [file_type]

        if parent_id:
            params["folder_path_or_id"] = parent_id

        if include_shared_drives:
            params["include_shared_drives"] = True

        if shared_drive_id:
            params["shared_drive_id"] = shared_drive_id

        if include_organization_domain_documents:
            params["include_organization_domain_documents"] = True

        if order_by:
            params["order_by"] = order_by

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
        # Build parameters for GoogleDrive.GetFileTreeStructure
        params = {}

        if include_shared_drives:
            params["include_shared_drives"] = True

        if restrict_to_shared_drive_id:
            params["restrict_to_shared_drive_id"] = restrict_to_shared_drive_id

        if include_organization_domain_documents:
            params["include_organization_domain_documents"] = True

        if order_by:
            params["order_by"] = order_by

        if limit:
            params["limit"] = limit

        result = execute_tool("GoogleDrive.GetFileTreeStructure", **params)

        # Parse the tree structure from the response
        def parse_node(data: dict) -> TreeNode:
            """Recursively parse a node from the API response."""
            children = []
            children_data = data.get("children", [])
            if isinstance(children_data, list):
                children = [parse_node(c) for c in children_data if isinstance(c, dict)]

            return TreeNode(
                id=data.get("id", ""),
                name=data.get("name", ""),
                mime_type=data.get("mimeType", ""),
                is_folder=data.get("mimeType") == "application/vnd.google-apps.folder",
                children=children,
            )

        def count_nodes(node: TreeNode) -> int:
            """Count total nodes in tree."""
            return 1 + sum(count_nodes(c) for c in node.children)

        # Handle various response formats
        root_node = None
        total_items = 0

        if isinstance(result, dict):
            root_node = parse_node(result)
            total_items = count_nodes(root_node)
        elif isinstance(result, list) and result:
            # If result is a list, create a virtual root
            children = [parse_node(item) for item in result if isinstance(item, dict)]
            root_node = TreeNode(
                id="root",
                name="Root",
                mime_type="application/vnd.google-apps.folder",
                is_folder=True,
                children=children,
            )
            total_items = count_nodes(root_node)

        return TreeResult(
            success=True,
            root=root_node,
            total_items=total_items,
            message=f"Retrieved tree with {total_items} item(s)",
        )

    except ArcadeToolError as e:
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
        result = execute_tool("GoogleDrive.WhoAmI")

        if not isinstance(result, dict):
            return UserInfo(
                success=False,
                email=None,
                name=None,
                shared_drives=[],
                raw_response={},
                message=f"Unexpected response format: {type(result).__name__}",
            )

        # Extract shared drives
        drives_data = result.get("sharedDrives", result.get("shared_drives", []))
        shared_drives = []
        for d in drives_data:
            drive_id = d.get("id", "")
            shared_drives.append(
                FileInfo(
                    id=drive_id,
                    name=d.get("name", ""),
                    mime_type="application/vnd.google-apps.folder",
                    url=build_drive_url(drive_id, is_folder=True) if drive_id else "",
                    is_folder=True,
                )
            )

        return UserInfo(
            success=True,
            email=result.get("email", result.get("emailAddress")),
            name=result.get("name", result.get("displayName")),
            shared_drives=shared_drives,
            raw_response=result,
            message="User info retrieved successfully",
        )

    except ArcadeToolError as e:
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

    This URL allows users to select files from their Google Drive
    and grant access to the application.

    Returns:
        str: The File Picker URL, or an error message if generation failed.
    """
    try:
        result = execute_tool("GoogleDrive.GenerateGoogleFilePickerUrl")

        if isinstance(result, str):
            return result

        if isinstance(result, dict):
            return result.get("url", result.get("picker_url", str(result)))

        return str(result)

    except ArcadeToolError as e:
        logger.error(f"Generate file picker URL failed: {e}")
        return f"Error: {e}"
