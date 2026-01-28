"""Claude tool definitions and execution dispatch for Google Drive operations.

Each tool wraps a DriveClient method and returns a JSON-serializable dict.
"""

from __future__ import annotations

import sys
import os

# Add project root to path so we can import src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.client import DriveClient

# Lazy-initialized client
_client: DriveClient | None = None


def _get_client() -> DriveClient:
    global _client
    if _client is None:
        _client = DriveClient()
    return _client


# ---------------------------------------------------------------------------
# Tool definitions in Anthropic tool-use format
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "name": "search_drive",
        "description": "Search for files and folders by name across all drives including Shared Drives. Searches recursively through all subfolders. Returns file IDs, names, types, and URLs. To search within a specific folder, first find its ID using search or list_folder, then pass that ID as parent_id.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term to find files/folders by name (searches recursively through all subfolders).",
                },
                "file_type": {
                    "type": "string",
                    "description": "Optional filter: 'folder', 'document', 'spreadsheet', 'presentation', 'pdf'.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default 50).",
                },
                "parent_id": {
                    "type": "string",
                    "description": "Optional folder ID to search within. If provided, only searches within this folder and its subfolders.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "list_folder",
        "description": "List the contents (files and subfolders) of a folder by its ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "folder_id": {
                    "type": "string",
                    "description": "The Google Drive folder ID.",
                },
            },
            "required": ["folder_id"],
        },
    },
    {
        "name": "create_folder",
        "description": "Create a new folder. Use for My Drive (no parent_id) or Shared Drives (provide parent_id).",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name for the new folder.",
                },
                "parent_id": {
                    "type": "string",
                    "description": "Parent folder ID. Required for Shared Drives.",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "rename_file",
        "description": "Rename a file or folder.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "ID of the file or folder to rename.",
                },
                "new_name": {
                    "type": "string",
                    "description": "The new name.",
                },
            },
            "required": ["file_id", "new_name"],
        },
    },
    {
        "name": "move_file",
        "description": "Move a file or folder to a different parent folder.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "ID of the file or folder to move.",
                },
                "new_parent_id": {
                    "type": "string",
                    "description": "ID of the destination folder.",
                },
            },
            "required": ["file_id", "new_parent_id"],
        },
    },
    {
        "name": "share_file",
        "description": "Share a file or folder with one or more email addresses.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "ID of the file or folder to share.",
                },
                "emails": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Email addresses to share with.",
                },
                "role": {
                    "type": "string",
                    "description": "Permission role: 'reader', 'writer', or 'commenter'. Default 'writer'.",
                },
            },
            "required": ["file_id", "emails"],
        },
    },
    {
        "name": "get_user_info",
        "description": "Get information about the authenticated Google Drive user including email, name, and list of Shared Drives.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "delete_file",
        "description": "Delete (trash) a file or folder. This moves it to trash, not permanent deletion.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "ID of the file or folder to delete.",
                },
            },
            "required": ["file_id"],
        },
    },
]


# ---------------------------------------------------------------------------
# Tool execution dispatch
# ---------------------------------------------------------------------------

def _drive_file_to_dict(f) -> dict:
    """Convert a DriveFile dataclass to a plain dict."""
    return {
        "id": f.id,
        "name": f.name,
        "mime_type": f.mime_type,
        "is_folder": f.is_folder,
        "web_view_link": f.web_view_link,
    }


def execute_tool(name: str, args: dict) -> dict:
    """Execute a tool by name with the given arguments.

    Returns a JSON-serializable dict with the result.
    """
    client = _get_client()

    if name == "search_drive":
        from src.drive.google_api import search_all
        result = search_all(
            args["query"],
            file_type=args.get("file_type"),
            max_results=args.get("max_results", 50),
            parent_id=args.get("parent_id"),
        )
        return {
            "success": result.success,
            "count": result.count,
            "files": [_drive_file_to_dict(f) for f in result.files],
            "error": result.error,
        }

    elif name == "list_folder":
        result = client.list_folder(args["folder_id"])
        return {
            "success": result.success,
            "folder_name": result.folder_name,
            "count": result.count,
            "files": [_drive_file_to_dict(f) for f in result.files],
            "error": result.error,
        }

    elif name == "create_folder":
        parent_id = args.get("parent_id")
        if parent_id:
            # create_folder_shared_drive returns GoogleFolderResult (web_view_link, error)
            result = client.create_folder_shared_drive(
                args["name"], parent_id=parent_id,
            )
            return {
                "success": result.success,
                "folder_id": result.folder_id,
                "folder_name": result.folder_name or args["name"],
                "web_view_link": result.web_view_link,
                "error": result.error,
            }
        else:
            # create_folder returns FolderResult (folder_url, message)
            result = client.create_folder(args["name"])
            return {
                "success": result.success,
                "folder_id": result.folder_id,
                "folder_name": args["name"],
                "web_view_link": result.folder_url,
                "message": result.message,
            }

    elif name == "rename_file":
        result = client.rename(args["file_id"], args["new_name"])
        return {
            "success": result.success,
            "file_id": result.file_id,
            "file_name": args["new_name"],
            "web_view_link": result.file_url,
            "message": result.message,
        }

    elif name == "move_file":
        result = client.move(args["file_id"], args["new_parent_id"])
        return {
            "success": result.success,
            "file_id": result.folder_id,
            "web_view_link": result.folder_url,
            "message": result.message,
        }

    elif name == "share_file":
        role = args.get("role", "writer")
        results = []
        for email in args["emails"]:
            from src.drive.google_api import share_file
            r = share_file(args["file_id"], email, role=role)
            results.append({
                "email": email,
                "success": r.success,
                "message": r.message,
            })
        return {"results": results}

    elif name == "get_user_info":
        user_info = client.get_user_info()
        shared_drives = client.get_all_shared_drives()
        user_info["shared_drives"] = [
            {"id": d.id, "name": d.name} for d in shared_drives
        ]
        return user_info

    elif name == "delete_file":
        success = client.delete(args["file_id"])
        return {"success": success}

    else:
        return {"error": f"Unknown tool: {name}"}
