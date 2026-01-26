# CLAUDE.md - Google Drive Automation with Arcade

## Project Intent

Build a **modular Python toolkit** for automating Google Drive operations using [Arcade](https://arcade.dev). The primary use case is **project management for professional services engagements** where:

- 100+ projects need organized folder structures
- Contractors receive inputs and deliver outputs via shared Google Drive folders
- Each project has a unique ID and folder (e.g., `[20] Build`, `[25] Review`)
- URLs must be retrieved and shared with contractors (often with "Contributor" permissions)

The toolkit must be:
1. **Modular** - Functions can be imported and composed
2. **Generalizable** - Works across different client engagements with varying folder structures
3. **Extensible** - Ready to add Google Sheets integration and LLM agent capabilities later

---

## Core Actions

The toolkit must support these 5 operations:

| Action | Description | Example |
|--------|-------------|---------|
| **Search** | Find file/folder by name or ID | "Find folder `[20] Build`" |
| **Download** | Download file or folder contents | Download deliverables from contractor |
| **Create Folder** | Create new folder in specified location | Create `[47] Build` in project directory |
| **Move** | Move file/folder to different location | Reorganize deliverables |
| **Get URL** | Get shareable link with permissions | Get Contributor link for contractor |

---

## Architecture

```
arcade-gdrive/
├── .env                    # API keys and configuration
├── .env.example            # Template for environment variables
├── requirements.txt        # Python dependencies
├── README.md               # User-facing documentation
│
├── src/
│   ├── __init__.py
│   ├── config.py           # Configuration and environment loading
│   ├── auth.py             # Arcade authentication helpers
│   ├── drive/
│   │   ├── __init__.py
│   │   ├── search.py       # Search operations
│   │   ├── download.py     # Download operations
│   │   ├── folders.py      # Create/move folder operations
│   │   ├── sharing.py      # URL retrieval and sharing
│   │   └── utils.py        # Common utilities (path parsing, etc.)
│   └── client.py           # Main ArcadeDriveClient class
│
├── scripts/
│   ├── batch_create_folders.py    # Example: Create folders for N projects
│   └── batch_get_urls.py          # Example: Get URLs for existing folders
│
└── tests/
    └── test_drive_operations.py
```

### Design Principles

1. **Single Responsibility**: Each module handles one type of operation
2. **Stateless Functions**: Functions take explicit parameters, no hidden state
3. **Consistent Return Types**: All functions return structured results (not raw API responses)
4. **Error Handling**: Graceful failures with informative messages
5. **Shared Drive Support**: All operations work with both "My Drive" and Shared Drives

---

## Prerequisites Setup

### 1. Google Cloud Project & OAuth Credentials (First-Time Setup)

Since you're working with Shared Drives and existing folders, you need your own OAuth credentials with broader scopes than Arcade's defaults.

#### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click the project dropdown (top-left, next to "Google Cloud")
3. Click **"New Project"**
4. Name it something like `gdrive-automation`
5. Click **"Create"**
6. Wait for creation, then select your new project from the dropdown

#### Step 2: Enable Google Drive API

1. In the left sidebar, go to **"APIs & Services" → "Library"**
2. Search for **"Google Drive API"**
3. Click on it, then click **"Enable"**

#### Step 3: Configure OAuth Consent Screen

1. Go to **"APIs & Services" → "OAuth consent screen"**
2. Select **"External"** (unless you have Google Workspace, then "Internal")
3. Click **"Create"**
4. Fill in required fields:
   - **App name**: `GDrive Automation`
   - **User support email**: Your email
   - **Developer contact email**: Your email
5. Click **"Save and Continue"**
6. On **Scopes** page, click **"Add or Remove Scopes"**
7. Find and select these scopes:
   - `https://www.googleapis.com/auth/drive` (full Drive access)
   - `https://www.googleapis.com/auth/drive.file`
   - `https://www.googleapis.com/auth/userinfo.email`
   - `https://www.googleapis.com/auth/userinfo.profile`
8. Click **"Update"**, then **"Save and Continue"**
9. On **Test users** page, click **"Add Users"**
10. Add your email address (e.g., `mo@thetaste.ai`)
11. Click **"Save and Continue"**, then **"Back to Dashboard"**

#### Step 4: Create OAuth Client ID

1. Go to **"APIs & Services" → "Credentials"**
2. Click **"+ Create Credentials" → "OAuth client ID"**
3. Select **"Web application"** as application type (NOT Desktop app - Arcade requires Web for redirect URIs)
4. Name it `GDrive Automation Web`
5. Leave **Authorized JavaScript origins** empty for now
6. Under **Authorized redirect URIs**, you'll add the Arcade URI in Step 6 below
7. Click **"Create"**

#### Step 5: Note Your Credentials

From the OAuth client you just created, note:
- **Client ID**: Something like `123456789-abc123.apps.googleusercontent.com`
- **Client Secret**: Something like `GOCSPX-xxxxx`

> ⚠️ **IMPORTANT**: Never share these credentials publicly or commit them to git.

#### Step 6: Configure Arcade and Add Redirect URI

This step connects Google and Arcade:

1. Go to [Arcade Dashboard](https://cloud.arcade.dev) → **OAuth Providers**
2. Click **"+ Add OAuth Provider"**
3. Select **Google** as provider type
4. Enter your **Client ID** and **Client Secret** from Step 5
5. Save the configuration
6. **Copy the Redirect URI** that Arcade displays (looks like `https://cloud.arcade.dev/api/v1/oauth/...`)
7. Go back to **Google Cloud Console → Credentials → Your OAuth Client**
8. Under **Authorized redirect URIs**, click **"+ Add URI"**
9. Paste the Arcade redirect URI
10. Click **Save**

> **Note**: Without the redirect URI, you'll get a "redirect_uri_mismatch" error during OAuth.

---

### 2. Arcade Account Setup

#### Step 1: Create Arcade Account

1. Go to [arcade.dev](https://arcade.dev) and sign up
2. Verify your email

#### Step 2: Get Arcade API Key

1. Go to your [Arcade dashboard](https://cloud.arcade.dev)
2. Navigate to **API Keys** section
3. Create a new API key
4. Copy and save it securely

> **Note**: The Google OAuth provider configuration was done in Step 6 above.

---

### 3. Environment Setup

#### Step 1: Create Project Directory

```bash
mkdir arcade-gdrive
cd arcade-gdrive
```

#### Step 2: Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

#### Step 3: Install Dependencies

Create `requirements.txt`:

```
arcadepy>=0.1.0
python-dotenv>=1.0.0
```

Install:

```bash
pip install -r requirements.txt
```

#### Step 4: Configure Environment Variables

Create `.env` file:

```bash
# Arcade Configuration
ARCADE_API_KEY=your_arcade_api_key_here
ARCADE_USER_ID=mo@thetaste.ai

# Default Shared Drive (optional - can override per function call)
# Get this from GoogleDrive.WhoAmI or from the Google Drive URL
DEFAULT_SHARED_DRIVE_ID=your_shared_drive_id_here
```

Create `.env.example` (for documentation):

```bash
# Arcade Configuration
ARCADE_API_KEY=
ARCADE_USER_ID=

# Default Shared Drive (optional)
DEFAULT_SHARED_DRIVE_ID=
```

Add to `.gitignore`:

```
.env
venv/
__pycache__/
*.pyc
.DS_Store
```

---

## Implementation

### File: `src/config.py`

```python
"""Configuration management for GDrive automation."""

import os
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import Optional

load_dotenv()


@dataclass
class Config:
    """Application configuration loaded from environment."""
    arcade_api_key: str
    arcade_user_id: str
    default_shared_drive_id: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        api_key = os.getenv("ARCADE_API_KEY")
        user_id = os.getenv("ARCADE_USER_ID")
        
        if not api_key:
            raise ValueError("ARCADE_API_KEY environment variable is required")
        if not user_id:
            raise ValueError("ARCADE_USER_ID environment variable is required")
        
        return cls(
            arcade_api_key=api_key,
            arcade_user_id=user_id,
            default_shared_drive_id=os.getenv("DEFAULT_SHARED_DRIVE_ID"),
        )


# Global config instance
config = Config.from_env()
```

---

### File: `src/auth.py`

```python
"""Authentication helpers for Arcade."""

import json
from arcadepy import Arcade
from typing import Any

from .config import config


def get_arcade_client() -> Arcade:
    """Get configured Arcade client instance."""
    return Arcade(api_key=config.arcade_api_key)


def authorize_tool(client: Arcade, tool_name: str) -> None:
    """
    Ensure a tool is authorized for the current user.
    
    If authorization is not complete, prints the auth URL and waits
    for the user to complete the OAuth flow.
    
    Args:
        client: Arcade client instance
        tool_name: Name of the tool to authorize (e.g., "GoogleDrive.SearchFiles")
    """
    auth_response = client.tools.authorize(
        tool_name=tool_name,
        user_id=config.arcade_user_id,
    )
    
    if auth_response.status != "completed":
        print(f"\n🔐 Authorization required for {tool_name}")
        print(f"   Please visit: {auth_response.url}")
        print("   Waiting for authorization...")
        client.auth.wait_for_completion(auth_response.id)
        print("   ✓ Authorization complete!\n")


def execute_tool(client: Arcade, tool_name: str, inputs: dict) -> Any:
    """
    Authorize and execute an Arcade tool.
    
    Args:
        client: Arcade client instance
        tool_name: Full tool name (e.g., "GoogleDrive.SearchFiles")
        inputs: Tool input parameters
        
    Returns:
        Tool output value
    """
    authorize_tool(client, tool_name)
    
    result = client.tools.execute(
        tool_name=tool_name,
        input=inputs,
        user_id=config.arcade_user_id,
    )
    
    return result.output.value
```

---

### File: `src/drive/utils.py`

```python
"""Utility functions for Google Drive operations."""

import re
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class ParsedPath:
    """Represents a parsed Google Drive path."""
    parts: list[str]
    filename: Optional[str]
    is_folder: bool
    
    @property
    def parent_path(self) -> str:
        """Get the parent directory path."""
        if len(self.parts) > 1:
            return "/".join(self.parts[:-1])
        return ""
    
    @property
    def name(self) -> str:
        """Get the file/folder name."""
        return self.parts[-1] if self.parts else ""


def parse_drive_path(path: str) -> ParsedPath:
    """
    Parse a Google Drive path into components.
    
    Handles both:
    - Relative paths: "folder/subfolder/file.txt"
    - Full local paths: "/Users/.../Shared drives/Product/..."
    
    Args:
        path: The path to parse
        
    Returns:
        ParsedPath object with parsed components
    """
    # Handle full local Google Drive paths
    if "Shared drives/" in path:
        # Extract everything after "Shared drives/DriveName/"
        match = re.search(r"Shared drives/[^/]+/(.+)", path)
        if match:
            path = match.group(1)
    
    # Clean up path
    path = path.strip("/")
    parts = [p for p in path.split("/") if p]
    
    # Determine if it's a folder (no extension or explicit folder markers)
    name = parts[-1] if parts else ""
    is_folder = "." not in name or name.startswith("[")
    
    return ParsedPath(
        parts=parts,
        filename=None if is_folder else name,
        is_folder=is_folder,
    )


def extract_project_id(folder_name: str) -> Optional[int]:
    """
    Extract project ID from folder name like "[20] Build".
    
    Args:
        folder_name: Folder name potentially containing [ID] prefix
        
    Returns:
        Project ID as integer, or None if not found
    """
    match = re.match(r"\[(\d+)\]", folder_name)
    if match:
        return int(match.group(1))
    return None


def format_folder_name(project_id: int, suffix: str) -> str:
    """
    Format a folder name with project ID prefix.
    
    Args:
        project_id: The project ID number
        suffix: The folder suffix (e.g., "Build", "Review")
        
    Returns:
        Formatted folder name like "[20] Build"
    """
    return f"[{project_id}] {suffix}"


def is_google_drive_id(value: str) -> bool:
    """
    Check if a string looks like a Google Drive file/folder ID.
    
    Google Drive IDs are typically 25-44 characters of alphanumeric
    characters, hyphens, and underscores.
    
    Args:
        value: String to check
        
    Returns:
        True if it looks like a Drive ID
    """
    if not value:
        return False
    # Drive IDs don't contain slashes or spaces
    if "/" in value or " " in value:
        return False
    # Drive IDs are typically 25-44 chars
    if len(value) < 20 or len(value) > 50:
        return False
    # Drive IDs are alphanumeric with hyphens and underscores
    return bool(re.match(r"^[a-zA-Z0-9_-]+$", value))
```

---

### File: `src/drive/search.py`

```python
"""Search operations for Google Drive."""

from typing import Optional, List, Literal
from dataclasses import dataclass

from ..auth import get_arcade_client, execute_tool
from ..config import config
from .utils import is_google_drive_id


@dataclass
class SearchResult:
    """Represents a single search result."""
    id: str
    name: str
    mime_type: str
    is_folder: bool
    path: Optional[str] = None
    web_view_link: Optional[str] = None
    

@dataclass 
class SearchResults:
    """Container for search results."""
    items: List[SearchResult]
    total_count: int
    query: str
    
    def first(self) -> Optional[SearchResult]:
        """Get the first result, or None if empty."""
        return self.items[0] if self.items else None
    
    def folders(self) -> List[SearchResult]:
        """Get only folder results."""
        return [item for item in self.items if item.is_folder]
    
    def files(self) -> List[SearchResult]:
        """Get only file results."""
        return [item for item in self.items if not item.is_folder]


def search(
    query: str,
    *,
    folder_path_or_id: Optional[str] = None,
    shared_drive_id: Optional[str] = None,
    include_shared_drives: bool = True,
    file_types: Optional[List[str]] = None,
    limit: int = 50,
) -> SearchResults:
    """
    Search for files and folders in Google Drive.
    
    Args:
        query: Search query (searches names and content)
        folder_path_or_id: Limit search to specific folder (path or ID)
        shared_drive_id: Limit search to specific shared drive
        include_shared_drives: Include all shared drives in search
        file_types: Filter by file types (e.g., ["folder", "document"])
        limit: Maximum results to return
        
    Returns:
        SearchResults containing matching items
        
    Example:
        >>> results = search("[20] Build")
        >>> if results.first():
        ...     print(f"Found: {results.first().name}")
    """
    client = get_arcade_client()
    
    # Use default shared drive if not specified and available
    if shared_drive_id is None and config.default_shared_drive_id:
        shared_drive_id = config.default_shared_drive_id
    
    inputs = {
        "query": query,
        "include_shared_drives": include_shared_drives,
        "limit": limit,
    }
    
    if folder_path_or_id:
        inputs["folder_path_or_id"] = folder_path_or_id
    if shared_drive_id:
        inputs["shared_drive_id"] = shared_drive_id
    if file_types:
        inputs["file_types"] = file_types
    
    result = execute_tool(client, "GoogleDrive.SearchFiles", inputs)
    
    # Parse results into structured format
    items = []
    if result and isinstance(result, list):
        for item in result:
            items.append(SearchResult(
                id=item.get("id", ""),
                name=item.get("name", ""),
                mime_type=item.get("mimeType", ""),
                is_folder=item.get("mimeType") == "application/vnd.google-apps.folder",
                path=item.get("path"),
                web_view_link=item.get("webViewLink"),
            ))
    
    return SearchResults(
        items=items,
        total_count=len(items),
        query=query,
    )


def find_folder(
    name: str,
    *,
    parent_path_or_id: Optional[str] = None,
    shared_drive_id: Optional[str] = None,
) -> Optional[SearchResult]:
    """
    Find a specific folder by name.
    
    This is a convenience wrapper around search() that returns
    the first matching folder.
    
    Args:
        name: Folder name to find (e.g., "[20] Build")
        parent_path_or_id: Parent folder to search within
        shared_drive_id: Shared drive to search
        
    Returns:
        SearchResult for the folder, or None if not found
        
    Example:
        >>> folder = find_folder("[20] Build")
        >>> if folder:
        ...     print(f"Found folder ID: {folder.id}")
    """
    results = search(
        query=name,
        folder_path_or_id=parent_path_or_id,
        shared_drive_id=shared_drive_id,
        file_types=["folder"],
        limit=10,
    )
    
    # Find exact match
    for item in results.folders():
        if item.name == name:
            return item
    
    # Return first folder if no exact match
    return results.first()


def find_by_id(file_or_folder_id: str) -> Optional[SearchResult]:
    """
    Get file/folder info by its ID.
    
    Args:
        file_or_folder_id: Google Drive file or folder ID
        
    Returns:
        SearchResult with item info, or None if not found
    """
    if not is_google_drive_id(file_or_folder_id):
        raise ValueError(f"Invalid Google Drive ID: {file_or_folder_id}")
    
    # Use search with the ID as the query
    # This is a workaround - ideally Arcade would have a GetFile tool
    results = search(query=file_or_folder_id, limit=1)
    return results.first()
```

---

### File: `src/drive/folders.py`

```python
"""Folder creation and management operations."""

from typing import Optional
from dataclasses import dataclass

from ..auth import get_arcade_client, execute_tool
from ..config import config
from .utils import format_folder_name


@dataclass
class FolderResult:
    """Result of a folder operation."""
    success: bool
    folder_id: Optional[str]
    folder_name: str
    message: str
    web_view_link: Optional[str] = None


def create_folder(
    folder_name: str,
    *,
    parent_path_or_id: Optional[str] = None,
    shared_drive_id: Optional[str] = None,
) -> FolderResult:
    """
    Create a new folder in Google Drive.
    
    Args:
        folder_name: Name for the new folder
        parent_path_or_id: Parent folder path or ID (None = root)
        shared_drive_id: Shared drive ID if creating in shared drive
        
    Returns:
        FolderResult with creation status and folder info
        
    Example:
        >>> result = create_folder("[20] Build", parent_path_or_id="Projects/Athena")
        >>> print(f"Created folder: {result.folder_id}")
    """
    client = get_arcade_client()
    
    # Use default shared drive if not specified
    if shared_drive_id is None and config.default_shared_drive_id:
        shared_drive_id = config.default_shared_drive_id
    
    inputs = {"folder_name": folder_name}
    
    if parent_path_or_id:
        inputs["parent_folder_path_or_id"] = parent_path_or_id
    if shared_drive_id:
        inputs["shared_drive_id"] = shared_drive_id
    
    try:
        result = execute_tool(client, "GoogleDrive.CreateFolder", inputs)
        
        return FolderResult(
            success=True,
            folder_id=result.get("id") if isinstance(result, dict) else None,
            folder_name=folder_name,
            message="Folder created successfully",
            web_view_link=result.get("webViewLink") if isinstance(result, dict) else None,
        )
    except Exception as e:
        return FolderResult(
            success=False,
            folder_id=None,
            folder_name=folder_name,
            message=f"Failed to create folder: {str(e)}",
        )


def create_project_folder(
    project_id: int,
    suffix: str,
    *,
    parent_path_or_id: Optional[str] = None,
    shared_drive_id: Optional[str] = None,
) -> FolderResult:
    """
    Create a project folder with standardized naming.
    
    Args:
        project_id: Project ID number (e.g., 20)
        suffix: Folder suffix (e.g., "Build", "Review")
        parent_path_or_id: Parent folder path or ID
        shared_drive_id: Shared drive ID
        
    Returns:
        FolderResult with creation status
        
    Example:
        >>> result = create_project_folder(20, "Build", parent_path_or_id="Projects")
        >>> # Creates folder named "[20] Build"
    """
    folder_name = format_folder_name(project_id, suffix)
    return create_folder(
        folder_name,
        parent_path_or_id=parent_path_or_id,
        shared_drive_id=shared_drive_id,
    )


def move_folder(
    source_path_or_id: str,
    destination_folder_path_or_id: str,
    *,
    new_name: Optional[str] = None,
    shared_drive_id: Optional[str] = None,
) -> FolderResult:
    """
    Move a folder to a different location.
    
    Args:
        source_path_or_id: Path or ID of folder to move
        destination_folder_path_or_id: Destination folder path or ID
        new_name: Optional new name for the folder after moving
        shared_drive_id: Shared drive ID if working in shared drive
        
    Returns:
        FolderResult with move status
        
    Example:
        >>> result = move_folder("[20] Build", "Archive/2024")
    """
    client = get_arcade_client()
    
    if shared_drive_id is None and config.default_shared_drive_id:
        shared_drive_id = config.default_shared_drive_id
    
    inputs = {
        "source_file_path_or_id": source_path_or_id,
        "destination_folder_path_or_id": destination_folder_path_or_id,
    }
    
    if new_name:
        inputs["new_filename"] = new_name
    if shared_drive_id:
        inputs["shared_drive_id"] = shared_drive_id
    
    try:
        result = execute_tool(client, "GoogleDrive.MoveFile", inputs)
        
        return FolderResult(
            success=True,
            folder_id=result.get("id") if isinstance(result, dict) else None,
            folder_name=new_name or source_path_or_id.split("/")[-1],
            message="Folder moved successfully",
        )
    except Exception as e:
        return FolderResult(
            success=False,
            folder_id=None,
            folder_name=source_path_or_id,
            message=f"Failed to move folder: {str(e)}",
        )
```

---

### File: `src/drive/sharing.py`

```python
"""Sharing and URL operations for Google Drive."""

from typing import Optional, List, Literal
from dataclasses import dataclass
from enum import Enum

from ..auth import get_arcade_client, execute_tool
from ..config import config
from .search import find_folder, SearchResult


class ShareRole(str, Enum):
    """Permission roles for sharing."""
    READER = "reader"           # View only
    COMMENTER = "commenter"     # View and comment
    WRITER = "writer"           # Edit (Contributor)
    

@dataclass
class ShareResult:
    """Result of a sharing operation."""
    success: bool
    file_id: str
    file_name: str
    web_view_link: Optional[str]
    message: str
    shared_with: List[str] = None


@dataclass
class UrlResult:
    """Result of URL retrieval."""
    success: bool
    file_id: Optional[str]
    file_name: str
    web_view_link: Optional[str]
    message: str


def get_shareable_url(
    file_or_folder_name: str,
    *,
    parent_path_or_id: Optional[str] = None,
    shared_drive_id: Optional[str] = None,
) -> UrlResult:
    """
    Get the shareable URL for a file or folder.
    
    Args:
        file_or_folder_name: Name of file/folder to get URL for
        parent_path_or_id: Parent folder to search within
        shared_drive_id: Shared drive ID
        
    Returns:
        UrlResult with URL if found
        
    Example:
        >>> result = get_shareable_url("[20] Build")
        >>> if result.success:
        ...     print(f"URL: {result.web_view_link}")
    """
    folder = find_folder(
        file_or_folder_name,
        parent_path_or_id=parent_path_or_id,
        shared_drive_id=shared_drive_id,
    )
    
    if folder:
        return UrlResult(
            success=True,
            file_id=folder.id,
            file_name=folder.name,
            web_view_link=folder.web_view_link,
            message="URL retrieved successfully",
        )
    else:
        return UrlResult(
            success=False,
            file_id=None,
            file_name=file_or_folder_name,
            web_view_link=None,
            message=f"Could not find: {file_or_folder_name}",
        )


def get_url_by_id(file_or_folder_id: str) -> UrlResult:
    """
    Get the shareable URL for a file or folder by its ID.
    
    Args:
        file_or_folder_id: Google Drive ID
        
    Returns:
        UrlResult with URL if found
    """
    from .search import find_by_id
    
    item = find_by_id(file_or_folder_id)
    
    if item:
        return UrlResult(
            success=True,
            file_id=item.id,
            file_name=item.name,
            web_view_link=item.web_view_link,
            message="URL retrieved successfully",
        )
    else:
        return UrlResult(
            success=False,
            file_id=file_or_folder_id,
            file_name="Unknown",
            web_view_link=None,
            message=f"Could not find item with ID: {file_or_folder_id}",
        )


def share_with_users(
    file_path_or_id: str,
    email_addresses: List[str],
    *,
    role: ShareRole = ShareRole.WRITER,
    send_notification: bool = True,
    message: Optional[str] = None,
    shared_drive_id: Optional[str] = None,
) -> ShareResult:
    """
    Share a file or folder with specific users.
    
    Args:
        file_path_or_id: Path or ID of file/folder to share
        email_addresses: List of email addresses to share with
        role: Permission role (default: WRITER/Contributor)
        send_notification: Send email notification to users
        message: Optional message in notification email
        shared_drive_id: Shared drive ID
        
    Returns:
        ShareResult with sharing status
        
    Example:
        >>> result = share_with_users(
        ...     "[20] Build",
        ...     ["contractor@email.com"],
        ...     role=ShareRole.WRITER,
        ...     message="Here's your project folder"
        ... )
    """
    client = get_arcade_client()
    
    if shared_drive_id is None and config.default_shared_drive_id:
        shared_drive_id = config.default_shared_drive_id
    
    inputs = {
        "file_path_or_id": file_path_or_id,
        "email_addresses": email_addresses,
        "role": role.value,
        "send_notification_email": send_notification,
    }
    
    if message:
        inputs["message"] = message
    if shared_drive_id:
        inputs["shared_drive_id"] = shared_drive_id
    
    try:
        result = execute_tool(client, "GoogleDrive.ShareFile", inputs)
        
        return ShareResult(
            success=True,
            file_id=result.get("id", "") if isinstance(result, dict) else "",
            file_name=file_path_or_id,
            web_view_link=result.get("webViewLink") if isinstance(result, dict) else None,
            message="Shared successfully",
            shared_with=email_addresses,
        )
    except Exception as e:
        return ShareResult(
            success=False,
            file_id="",
            file_name=file_path_or_id,
            web_view_link=None,
            message=f"Failed to share: {str(e)}",
            shared_with=[],
        )


def create_folder_and_get_url(
    folder_name: str,
    *,
    parent_path_or_id: Optional[str] = None,
    shared_drive_id: Optional[str] = None,
    share_with: Optional[List[str]] = None,
    share_role: ShareRole = ShareRole.WRITER,
) -> UrlResult:
    """
    Create a folder and immediately get its shareable URL.
    
    Convenience function that combines create + URL retrieval.
    Optionally shares with specified users.
    
    Args:
        folder_name: Name for the new folder
        parent_path_or_id: Parent folder path or ID
        shared_drive_id: Shared drive ID
        share_with: Optional list of emails to share with
        share_role: Role for sharing (default: WRITER)
        
    Returns:
        UrlResult with the folder URL
        
    Example:
        >>> result = create_folder_and_get_url(
        ...     "[20] Build",
        ...     parent_path_or_id="Projects/Athena",
        ...     share_with=["contractor@email.com"]
        ... )
        >>> print(f"Folder URL: {result.web_view_link}")
    """
    from .folders import create_folder
    
    # Create the folder
    create_result = create_folder(
        folder_name,
        parent_path_or_id=parent_path_or_id,
        shared_drive_id=shared_drive_id,
    )
    
    if not create_result.success:
        return UrlResult(
            success=False,
            file_id=None,
            file_name=folder_name,
            web_view_link=None,
            message=create_result.message,
        )
    
    # Share if requested
    if share_with and create_result.folder_id:
        share_with_users(
            create_result.folder_id,
            share_with,
            role=share_role,
            shared_drive_id=shared_drive_id,
        )
    
    return UrlResult(
        success=True,
        file_id=create_result.folder_id,
        file_name=folder_name,
        web_view_link=create_result.web_view_link,
        message="Folder created successfully",
    )
```

---

### File: `src/drive/download.py`

```python
"""Download operations for Google Drive."""

import base64
from typing import Optional
from dataclasses import dataclass
from pathlib import Path

from ..auth import get_arcade_client, execute_tool
from ..config import config


@dataclass
class DownloadResult:
    """Result of a download operation."""
    success: bool
    file_name: str
    local_path: Optional[str]
    file_size: Optional[int]
    message: str
    requires_chunked: bool = False


def download_file(
    file_path_or_id: str,
    *,
    save_to: Optional[str] = None,
    shared_drive_id: Optional[str] = None,
) -> DownloadResult:
    """
    Download a file from Google Drive.
    
    For large files (>5MB), this will indicate that chunked download
    is required.
    
    Args:
        file_path_or_id: Path or ID of file to download
        save_to: Local path to save file (default: current directory)
        shared_drive_id: Shared drive ID
        
    Returns:
        DownloadResult with download status and local path
        
    Example:
        >>> result = download_file("Reports/Q4-Summary.pdf", save_to="./downloads/")
        >>> if result.success:
        ...     print(f"Saved to: {result.local_path}")
    """
    client = get_arcade_client()
    
    if shared_drive_id is None and config.default_shared_drive_id:
        shared_drive_id = config.default_shared_drive_id
    
    inputs = {"file_path_or_id": file_path_or_id}
    if shared_drive_id:
        inputs["shared_drive_id"] = shared_drive_id
    
    try:
        result = execute_tool(client, "GoogleDrive.DownloadFile", inputs)
        
        if isinstance(result, dict):
            # Check if chunked download is required
            if result.get("requires_chunked_download"):
                return DownloadResult(
                    success=False,
                    file_name=result.get("name", file_path_or_id),
                    local_path=None,
                    file_size=result.get("size"),
                    message="File too large - use download_file_chunked()",
                    requires_chunked=True,
                )
            
            # Decode and save the file
            content_b64 = result.get("content", "")
            file_name = result.get("name", "downloaded_file")
            
            if content_b64:
                content = base64.b64decode(content_b64)
                
                # Determine save path
                if save_to:
                    save_path = Path(save_to)
                    if save_path.is_dir():
                        save_path = save_path / file_name
                else:
                    save_path = Path(file_name)
                
                # Write file
                save_path.parent.mkdir(parents=True, exist_ok=True)
                save_path.write_bytes(content)
                
                return DownloadResult(
                    success=True,
                    file_name=file_name,
                    local_path=str(save_path),
                    file_size=len(content),
                    message="Download complete",
                )
        
        return DownloadResult(
            success=False,
            file_name=file_path_or_id,
            local_path=None,
            file_size=None,
            message="Unexpected response format",
        )
        
    except Exception as e:
        return DownloadResult(
            success=False,
            file_name=file_path_or_id,
            local_path=None,
            file_size=None,
            message=f"Download failed: {str(e)}",
        )


def download_file_chunked(
    file_path_or_id: str,
    *,
    save_to: str,
    shared_drive_id: Optional[str] = None,
    chunk_size: int = 5242880,  # 5MB
    on_progress: Optional[callable] = None,
) -> DownloadResult:
    """
    Download a large file in chunks.
    
    Use this for files >5MB that require chunked download.
    
    Args:
        file_path_or_id: Path or ID of file to download
        save_to: Local path to save file
        shared_drive_id: Shared drive ID
        chunk_size: Chunk size in bytes (default: 5MB, max: 5MB)
        on_progress: Optional callback(bytes_downloaded, total_bytes)
        
    Returns:
        DownloadResult with download status
        
    Example:
        >>> def progress(downloaded, total):
        ...     print(f"Progress: {downloaded}/{total} bytes")
        >>> result = download_file_chunked(
        ...     "LargeFile.zip",
        ...     save_to="./downloads/LargeFile.zip",
        ...     on_progress=progress
        ... )
    """
    client = get_arcade_client()
    
    if shared_drive_id is None and config.default_shared_drive_id:
        shared_drive_id = config.default_shared_drive_id
    
    save_path = Path(save_to)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    
    start_byte = 0
    total_downloaded = 0
    file_name = file_path_or_id.split("/")[-1]
    
    try:
        with open(save_path, "wb") as f:
            while True:
                inputs = {
                    "file_path_or_id": file_path_or_id,
                    "start_byte": start_byte,
                    "chunk_size": min(chunk_size, 5242880),
                }
                if shared_drive_id:
                    inputs["shared_drive_id"] = shared_drive_id
                
                result = execute_tool(client, "GoogleDrive.DownloadFileChunk", inputs)
                
                if isinstance(result, dict):
                    content_b64 = result.get("content", "")
                    if content_b64:
                        content = base64.b64decode(content_b64)
                        f.write(content)
                        total_downloaded += len(content)
                        
                        if on_progress:
                            total_size = result.get("total_size", total_downloaded)
                            on_progress(total_downloaded, total_size)
                    
                    # Check if this was the final chunk
                    if result.get("is_final_chunk", False):
                        file_name = result.get("name", file_name)
                        break
                    
                    start_byte = total_downloaded
                else:
                    break
        
        return DownloadResult(
            success=True,
            file_name=file_name,
            local_path=str(save_path),
            file_size=total_downloaded,
            message="Download complete",
        )
        
    except Exception as e:
        return DownloadResult(
            success=False,
            file_name=file_path_or_id,
            local_path=None,
            file_size=total_downloaded,
            message=f"Chunked download failed: {str(e)}",
        )
```

---

### File: `src/drive/__init__.py`

```python
"""Google Drive operations module."""

from .search import search, find_folder, find_by_id, SearchResult, SearchResults
from .folders import create_folder, create_project_folder, move_folder, FolderResult
from .sharing import (
    get_shareable_url,
    get_url_by_id,
    share_with_users,
    create_folder_and_get_url,
    ShareRole,
    ShareResult,
    UrlResult,
)
from .download import download_file, download_file_chunked, DownloadResult
from .utils import (
    parse_drive_path,
    extract_project_id,
    format_folder_name,
    is_google_drive_id,
)

__all__ = [
    # Search
    "search",
    "find_folder",
    "find_by_id",
    "SearchResult",
    "SearchResults",
    # Folders
    "create_folder",
    "create_project_folder",
    "move_folder",
    "FolderResult",
    # Sharing
    "get_shareable_url",
    "get_url_by_id",
    "share_with_users",
    "create_folder_and_get_url",
    "ShareRole",
    "ShareResult",
    "UrlResult",
    # Download
    "download_file",
    "download_file_chunked",
    "DownloadResult",
    # Utils
    "parse_drive_path",
    "extract_project_id",
    "format_folder_name",
    "is_google_drive_id",
]
```

---

### File: `src/__init__.py`

```python
"""Arcade Google Drive automation toolkit."""

from .drive import *
from .config import config

__version__ = "0.1.0"
```

---

### File: `src/client.py`

```python
"""High-level client for Google Drive operations."""

from typing import Optional, List

from .config import config
from .drive import (
    search,
    find_folder,
    create_folder,
    create_project_folder,
    move_folder,
    get_shareable_url,
    share_with_users,
    create_folder_and_get_url,
    download_file,
    download_file_chunked,
    ShareRole,
)


class ArcadeDriveClient:
    """
    High-level client for Google Drive operations via Arcade.
    
    Provides a clean interface to all drive operations with
    consistent configuration.
    
    Example:
        >>> client = ArcadeDriveClient(shared_drive_id="abc123")
        >>> 
        >>> # Search for a folder
        >>> results = client.search("[20] Build")
        >>> 
        >>> # Create a project folder and get URL
        >>> url_result = client.create_project_folder_with_url(
        ...     project_id=20,
        ...     suffix="Build",
        ...     parent_path="Projects/Athena"
        ... )
        >>> print(f"Folder URL: {url_result.web_view_link}")
    """
    
    def __init__(
        self,
        shared_drive_id: Optional[str] = None,
    ):
        """
        Initialize the client.
        
        Args:
            shared_drive_id: Default shared drive ID (overrides env config)
        """
        self.shared_drive_id = shared_drive_id or config.default_shared_drive_id
    
    def search(self, query: str, **kwargs):
        """Search for files/folders."""
        kwargs.setdefault("shared_drive_id", self.shared_drive_id)
        return search(query, **kwargs)
    
    def find_folder(self, name: str, **kwargs):
        """Find a specific folder by name."""
        kwargs.setdefault("shared_drive_id", self.shared_drive_id)
        return find_folder(name, **kwargs)
    
    def create_folder(self, name: str, parent_path_or_id: Optional[str] = None, **kwargs):
        """Create a new folder."""
        kwargs.setdefault("shared_drive_id", self.shared_drive_id)
        return create_folder(name, parent_path_or_id=parent_path_or_id, **kwargs)
    
    def create_project_folder(
        self,
        project_id: int,
        suffix: str,
        parent_path_or_id: Optional[str] = None,
        **kwargs
    ):
        """Create a project folder with [ID] prefix."""
        kwargs.setdefault("shared_drive_id", self.shared_drive_id)
        return create_project_folder(
            project_id, suffix, parent_path_or_id=parent_path_or_id, **kwargs
        )
    
    def create_project_folder_with_url(
        self,
        project_id: int,
        suffix: str,
        parent_path_or_id: Optional[str] = None,
        share_with: Optional[List[str]] = None,
        **kwargs
    ):
        """Create a project folder and return its URL."""
        from .drive.utils import format_folder_name
        
        folder_name = format_folder_name(project_id, suffix)
        kwargs.setdefault("shared_drive_id", self.shared_drive_id)
        return create_folder_and_get_url(
            folder_name,
            parent_path_or_id=parent_path_or_id,
            share_with=share_with,
            **kwargs
        )
    
    def move_folder(self, source: str, destination: str, **kwargs):
        """Move a folder to a new location."""
        kwargs.setdefault("shared_drive_id", self.shared_drive_id)
        return move_folder(source, destination, **kwargs)
    
    def get_url(self, file_or_folder_name: str, **kwargs):
        """Get shareable URL for a file/folder."""
        kwargs.setdefault("shared_drive_id", self.shared_drive_id)
        return get_shareable_url(file_or_folder_name, **kwargs)
    
    def share(
        self,
        file_path_or_id: str,
        email_addresses: List[str],
        role: ShareRole = ShareRole.WRITER,
        **kwargs
    ):
        """Share a file/folder with users."""
        kwargs.setdefault("shared_drive_id", self.shared_drive_id)
        return share_with_users(file_path_or_id, email_addresses, role=role, **kwargs)
    
    def download(self, file_path_or_id: str, save_to: Optional[str] = None, **kwargs):
        """Download a file."""
        kwargs.setdefault("shared_drive_id", self.shared_drive_id)
        return download_file(file_path_or_id, save_to=save_to, **kwargs)
    
    def download_large(self, file_path_or_id: str, save_to: str, **kwargs):
        """Download a large file in chunks."""
        kwargs.setdefault("shared_drive_id", self.shared_drive_id)
        return download_file_chunked(file_path_or_id, save_to=save_to, **kwargs)
```

---

## Usage Examples

### Basic Usage (Importing Functions)

```python
from src.drive import search, find_folder, get_shareable_url, create_folder

# Search for a folder
results = search("[20] Build")
print(f"Found {results.total_count} results")

# Find a specific folder
folder = find_folder("[20] Build")
if folder:
    print(f"Folder ID: {folder.id}")
    print(f"URL: {folder.web_view_link}")

# Get URL for a folder
url_result = get_shareable_url("[20] Build")
if url_result.success:
    print(f"Shareable URL: {url_result.web_view_link}")

# Create a new folder
result = create_folder(
    "[47] Build",
    parent_path_or_id="_FULL DELIVERABLE/[47] New Project"
)
print(f"Created: {result.folder_id}")
```

### Using the Client Class

```python
from src.client import ArcadeDriveClient

# Initialize with your shared drive
client = ArcadeDriveClient(shared_drive_id="your_shared_drive_id")

# Create project folder and get URL in one call
result = client.create_project_folder_with_url(
    project_id=20,
    suffix="Build",
    parent_path_or_id="_FULL DELIVERABLE/[20] Cement Banking Teaser"
)
print(f"Folder URL: {result.web_view_link}")

# Find and get URL for existing folder
url = client.get_url("[25] Build")
print(f"URL: {url.web_view_link}")
```

### Batch Script: Create Multiple Project Folders

```python
# scripts/batch_create_folders.py

from src.client import ArcadeDriveClient

# Configuration
SHARED_DRIVE_ID = "your_shared_drive_id"
BASE_PATH = "_FULL DELIVERABLE"
PROJECTS = [
    {"id": 20, "name": "Cement Banking Teaser", "suffix": "Build"},
    {"id": 25, "name": "Consulting HR Strategy", "suffix": "Build"},
    {"id": 31, "name": "Tech Startup Pitch", "suffix": "Build"},
    # ... add more projects
]

def main():
    client = ArcadeDriveClient(shared_drive_id=SHARED_DRIVE_ID)
    
    results = []
    for project in PROJECTS:
        parent_path = f"{BASE_PATH}/[{project['id']}] {project['name']}"
        
        result = client.create_project_folder_with_url(
            project_id=project["id"],
            suffix=project["suffix"],
            parent_path_or_id=parent_path,
        )
        
        results.append({
            "project_id": project["id"],
            "folder_name": f"[{project['id']}] {project['suffix']}",
            "url": result.web_view_link if result.success else "FAILED",
            "status": "✓" if result.success else "✗",
        })
        
        print(f"{results[-1]['status']} Project {project['id']}: {results[-1]['url']}")
    
    # Output for copy-paste to spreadsheet
    print("\n--- URLs for Spreadsheet (Tab-separated) ---")
    for r in results:
        print(f"{r['project_id']}\t{r['url']}")

if __name__ == "__main__":
    main()
```

### Batch Script: Get URLs for Existing Folders

```python
# scripts/batch_get_urls.py

from src.client import ArcadeDriveClient

# List of folder names to find
FOLDERS_TO_FIND = [
    "[20] Build",
    "[25] Build",
    "[31] Build",
    "[35] Build",
]

def main():
    client = ArcadeDriveClient()
    
    print("Folder Name\tURL")
    print("-" * 60)
    
    for folder_name in FOLDERS_TO_FIND:
        result = client.get_url(folder_name)
        if result.success:
            print(f"{folder_name}\t{result.web_view_link}")
        else:
            print(f"{folder_name}\tNOT FOUND")

if __name__ == "__main__":
    main()
```

---

## Future Extensibility

### Google Sheets Integration (Planned)

When ready to add Google Sheets support:

1. Add Arcade's Google Sheets tools to your setup
2. Create `src/sheets/` module following same pattern
3. Create combined scripts like:

```python
# Future: scripts/create_folders_and_update_sheet.py

from src.client import ArcadeDriveClient
from src.sheets import SheetsClient  # Future module

drive = ArcadeDriveClient()
sheets = SheetsClient()

# Read project IDs from sheet
projects = sheets.read_range("Sheet1!A4:A100")

for row_num, project_id in enumerate(projects, start=4):
    # Create folder and get URL
    result = drive.create_project_folder_with_url(
        project_id=int(project_id),
        suffix="Build",
        parent_path_or_id=f"_FULL DELIVERABLE/[{project_id}] ProjectName"
    )
    
    # Write URL back to column E
    if result.success:
        sheets.write_cell(f"Sheet1!E{row_num}", result.web_view_link)
```

### LLM Agent Mode (Planned)

The modular design allows easy wrapping with an LLM agent:

```python
# Future: agent.py

from src.client import ArcadeDriveClient
from openai import OpenAI

client = ArcadeDriveClient()

# Expose functions as tools for the LLM
tools = [
    {
        "name": "search_drive",
        "function": client.search,
        "description": "Search Google Drive for files/folders"
    },
    {
        "name": "get_folder_url", 
        "function": client.get_url,
        "description": "Get shareable URL for a folder"
    },
    # ... more tools
]

# Then use standard LLM tool-calling pattern
```

---

## Troubleshooting

### Common Issues

**"Authorization required" keeps appearing**
- Ensure you've set up custom OAuth credentials with `drive` scope
- Check that your email is added as a test user in Google Cloud Console

**"File not found" for files you can see**
- The `drive.file` scope only sees files your app has accessed
- Use `GenerateGoogleFilePickerUrl` to grant access to specific folders
- Or ensure you're using custom OAuth with full `drive` scope

**Shared Drive operations fail**
- Ensure `shared_drive_id` is set (in .env or passed to functions)
- Verify you have access to the Shared Drive

**Large file downloads fail**
- Use `download_file_chunked()` for files > 5MB

### Getting Your Shared Drive ID

**Method 1: From Google Drive URL**
1. Open Google Drive in browser
2. Click on **"Shared drives"** in the left sidebar
3. Click on your Shared Drive (e.g., "Product")
4. Look at the URL: `https://drive.google.com/drive/folders/XXXXXX`
5. The `XXXXXX` part is your Shared Drive ID

**Method 2: Using the WhoAmI Tool**
```python
from src.auth import get_arcade_client, execute_tool

client = get_arcade_client()
result = execute_tool(client, "GoogleDrive.WhoAmI", {})
print(result)  # Shows your shared drives and their IDs
```

**For your setup**, based on the path you shared:
`/Users/MTalib/Library/CloudStorage/GoogleDrive-mo@thetaste.ai/Shared drives/Product/...`

Your Shared Drive is named **"Product"**. Use Method 1 or 2 to get its ID.

---

## Testing

### Verify Setup

Run this first to ensure everything is configured correctly:

```python
# test_connection.py

from src.auth import get_arcade_client, execute_tool

def test_setup():
    print("Testing Arcade + Google Drive setup...\n")
    
    try:
        client = get_arcade_client()
        print("✓ Arcade client created")
        
        # This will trigger OAuth if not already authorized
        result = execute_tool(client, "GoogleDrive.WhoAmI", {})
        
        print("✓ Google Drive connection successful!")
        print(f"\nUser: {result.get('email', 'Unknown')}")
        print(f"Name: {result.get('name', 'Unknown')}")
        
        # List shared drives
        shared_drives = result.get('sharedDrives', [])
        if shared_drives:
            print(f"\nShared Drives ({len(shared_drives)}):")
            for drive in shared_drives:
                print(f"  - {drive.get('name')}: {drive.get('id')}")
        else:
            print("\nNo Shared Drives found (or not accessible with current scope)")
            
    except Exception as e:
        print(f"✗ Setup failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Check ARCADE_API_KEY in .env")
        print("  2. Check ARCADE_USER_ID in .env")
        print("  3. Verify OAuth redirect URI is configured in Google Cloud Console")
        print("  4. Ensure you're added as a test user in Google Cloud Console")

if __name__ == "__main__":
    test_setup()
```

Run it:
```bash
python test_connection.py
```

**Expected output**: You'll see your email, name, and list of Shared Drives with their IDs. Copy the ID of the Shared Drive you need (e.g., "Product") into your `.env` file.

### Quick Sanity Check

Once setup is verified, test the search functionality:

```python
# test_connection.py

from src.drive import search

try:
    results = search("test")
    print(f"✓ Connected! Found {results.total_count} results")
except Exception as e:
    print(f"✗ Connection failed: {e}")
```

---

## Summary

This toolkit provides:

| Need | Solution |
|------|----------|
| Search files/folders | `search()`, `find_folder()` |
| Download files | `download_file()`, `download_file_chunked()` |
| Create folders | `create_folder()`, `create_project_folder()` |
| Move folders | `move_folder()` |
| Get shareable URLs | `get_shareable_url()`, `get_url_by_id()` |
| Share with users | `share_with_users()` |
| Combined operations | `create_folder_and_get_url()` |
| High-level client | `ArcadeDriveClient` |

All functions work with both paths and Google Drive IDs, support Shared Drives, and return structured result objects for easy error handling.

---

## Implementation Session Log (January 2026)

### What Was Completed

**1. Full Project Structure Created**

All 17 files in the architecture were created at `/Users/MTalib/workspace_repos/Gdrive Automation/arcade-gdrive/`:

```
arcade-gdrive/
├── .env                    # Configured with credentials
├── .env.example            # Template
├── .gitignore              # Python ignores
├── requirements.txt        # arcadepy, python-dotenv, httpx[socks]
├── src/
│   ├── __init__.py
│   ├── config.py           # Lazy loading pattern
│   ├── auth.py             # Singleton client + auth caching
│   ├── drive/
│   │   ├── __init__.py     # All exports
│   │   ├── utils.py        # Validation, URL builders
│   │   ├── search.py       # Search, find_by_name, list_shared_drives
│   │   ├── folders.py      # Create, move, nested folders
│   │   ├── sharing.py      # Share, create_folder_and_share
│   │   └── download.py     # Chunked download with safety limits
│   └── client.py           # High-level ArcadeDriveClient
├── tests/
│   ├── __init__.py
│   └── test_connection.py  # Setup verification script
└── scripts/
    ├── batch_create_folders.py
    └── batch_get_urls.py
```

**2. Critical Fixes Applied**

All fixes from the implementation plan were incorporated:

| Fix | Implementation |
|-----|----------------|
| Chunked download infinite loop | Added `max_iterations=10000` safeguard in `download.py` |
| Empty chunk handling | Check for empty `content_b64` and return error |
| Success=True with None folder_id | Validate API response has `id` before returning success |
| Silent sharing failures | Check and report `share_result.success` in combined operations |
| Singleton client | `_client` global in `auth.py`, reused across calls |
| Authorization caching | `_authorized_tools: set[str]` avoids redundant auth calls |
| Mutable default argument | `field(default_factory=list)` for `shared_with` |
| Lazy config loading | `get_config()` function instead of global instantiation |
| Input validation | `validate_file_id()`, `validate_folder_name()` in utils |

**3. Python 3.9 Compatibility**

Added `from __future__ import annotations` to files using `str | Path` union syntax:
- `src/drive/download.py`
- `src/client.py`

**4. Correct Arcade Tool Names**

Updated all tool names to match Arcade's GoogleDrive toolkit:

| Original (Wrong) | Corrected |
|------------------|-----------|
| `Google.SearchFiles` | `GoogleDrive.SearchFiles` |
| `Google.CreateFolder` | `GoogleDrive.CreateFolder` |
| `Google.MoveFile` | `GoogleDrive.MoveFile` |
| `Google.ShareFile` | `GoogleDrive.ShareFile` |
| `Google.DownloadFile` | `GoogleDrive.DownloadFile` |
| `Google.GetUserInfo` | `GoogleDrive.WhoAmI` |

**5. Dependencies Installed**

```bash
pip install arcadepy python-dotenv httpx[socks]
```

---

### Current Roadblock: OAuth Authorization

**Status**: Blocked - Awaiting Arcade Support Response

**Symptom**: After completing Google OAuth consent screen successfully, Arcade's callback returns `access_denied` error.

**Error Details**:
```
Authorization error
There was an error during authorization. Please try again or contact support.
Error Type: access_denied
Flow ID: Not available
```

**What Was Tried**:

1. ✅ Created Google Cloud project with Drive API enabled
2. ✅ Configured OAuth consent screen with correct scopes:
   - `https://www.googleapis.com/auth/drive`
   - `https://www.googleapis.com/auth/drive.file`
   - `https://www.googleapis.com/auth/userinfo.email`
   - `https://www.googleapis.com/auth/userinfo.profile`
3. ✅ Added test user: `Mo@thetaste.ai`
4. ✅ Created OAuth Web Application credentials
5. ✅ Created custom OAuth provider in Arcade
6. ✅ Added Arcade redirect URI to Google: `https://cloud.arcade.dev/api/v1/oauth/f4c6b_ap_adxxMN1w61iv/callback`
7. ✅ Verified Client ID matches between Google and Arcade
8. ✅ Created fresh Client Secret and copied to Arcade
9. ✅ Completed Google consent screen successfully
10. ❌ Arcade callback returns `access_denied`

**Root Cause**: Unknown - appears to be an issue with Arcade's OAuth callback handler, not Google's configuration.

**Support Ticket**: Submitted to Arcade support (arcade.dev) on January 23, 2026.

---

### Configuration Reference

**Current `.env` file**:
```bash
ARCADE_API_KEY=arc_proj14pQwtZdSpQtZQz7gjCotc4CkrQD9S9zmePfHtUi3ikgV4B8B2h
ARCADE_USER_ID=Mo@thetaste.ai
```

**Google Cloud OAuth Client**:
- Project: gdrive-automation (or similar)
- Application Type: Web application
- Redirect URI: `https://cloud.arcade.dev/api/v1/oauth/f4c6b_ap_adxxMN1w61iv/callback`

**Arcade OAuth Provider ID**: `f4c6b_ap_adxxMN1w61iv`

---

### Steps to Resume

Once Arcade support resolves the OAuth issue:

1. **Test Connection**:
   ```bash
   cd "/Users/MTalib/workspace_repos/Gdrive Automation/arcade-gdrive"
   source venv/bin/activate
   python tests/test_connection.py
   ```

2. **Expected Output**:
   - Authorization URL will be printed
   - Complete OAuth in browser
   - See your email, name, and Shared Drives listed

3. **Get Shared Drive ID**:
   - Look for "Product" in the Shared Drives list
   - Copy its ID to `.env` as `DEFAULT_SHARED_DRIVE_ID`

4. **Test Search**:
   ```python
   from src.drive import search
   results = search("test")
   print(f"Found {results.total_count} results")
   ```

5. **Test Folder Creation**:
   ```python
   from src.drive import create_folder
   result = create_folder("Test Folder")
   print(f"Success: {result.success}, ID: {result.folder_id}")
   ```

---

### Checkpoint Best Practices

When resuming work on this project:

**1. Reference Files**:
- This `CLAUDE.md` - Contains full implementation plan and session log
- `/Users/MTalib/.claude/plans/keen-honking-finch.md` - Original implementation plan
- `/Users/MTalib/workspace_repos/Gdrive Automation/gdrive_arcade.md` - Arcade toolkit reference

**2. Quick Context Commands**:
```bash
# Check project structure
ls -la "/Users/MTalib/workspace_repos/Gdrive Automation/arcade-gdrive/src/"

# Check current .env
cat "/Users/MTalib/workspace_repos/Gdrive Automation/arcade-gdrive/.env"

# Test if OAuth is working
cd "/Users/MTalib/workspace_repos/Gdrive Automation/arcade-gdrive"
source venv/bin/activate
python tests/test_connection.py
```

**3. Key Files to Review**:
- `src/auth.py:84-113` - Authorization flow with URL printing
- `src/drive/search.py` - Main search implementation
- `src/drive/folders.py` - Folder creation with validation
- `tests/test_connection.py` - Setup verification

**4. What's Left After OAuth Fix**:
- [ ] Complete connection test successfully
- [ ] Get Shared Drive ID for "Product"
- [ ] Test search functionality
- [ ] Test folder creation in Shared Drive
- [ ] Test batch scripts
- [ ] Add to production workflow
