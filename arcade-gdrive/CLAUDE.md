# CLAUDE.md - Google Drive Automation Toolkit

## Project Overview

Python library for automating Google Drive operations, designed for professional services project management with 100+ project folders.

## Architecture Decision: Direct Google API

This project uses **direct Google API** instead of Arcade AI for Drive operations.

### Why Direct Google API?

| Aspect | Arcade AI | Direct Google API |
|--------|-----------|-------------------|
| **Scope** | `drive.file` (app-created files only) | `drive` (all files) |
| **Shared Drive Access** | Limited to app-created folders | Full access |
| **Existing Files** | Cannot access pre-existing content | Full access |
| **Authentication** | Arcade OAuth wrapper | Standard Google OAuth 2.0 |
| **Dependencies** | Requires `arcadepy` | Only `google-api-python-client` |

### Scope Limitations Explained

Arcade's Google integration uses the `drive.file` scope, which is designed for applications that only need to access files they create. This scope:
- Can create new files and folders
- Can only access files/folders the app has created
- Cannot see or modify pre-existing Drive content

For workflows requiring access to existing Shared Drive content (like managing contractor folders), the full `drive` scope provides broader access.

## File Structure

```
src/
├── auth.py              # Google OAuth authentication
├── config.py            # Environment configuration
├── client.py            # High-level DriveClient class
├── drive/
│   ├── google_api.py    # Direct Google API operations (PRIMARY)
│   ├── search.py        # Search operations
│   ├── folders.py       # Folder creation/management
│   ├── files.py         # File operations (rename, upload)
│   ├── sharing.py       # Sharing permissions
│   ├── download.py      # File downloads
│   └── utils.py         # URL builders, validators
```

## Authentication Setup

### Required: Google Cloud Project

1. Create project at [Google Cloud Console](https://console.cloud.google.com/)
2. Enable Google Drive API
3. Configure OAuth consent screen with scopes:
   - `https://www.googleapis.com/auth/drive`
   - `https://www.googleapis.com/auth/drive.metadata.readonly`
4. Create OAuth 2.0 Desktop credentials
5. Download `credentials.json` to project root

### Environment Variables

```bash
# .env file
GOOGLE_CREDENTIALS_FILE=credentials.json  # Path to OAuth credentials
GOOGLE_TOKEN_FILE=token.json              # Path to store access token

# Optional
DEFAULT_SHARED_DRIVE_ID=                  # Default Shared Drive ID
DEFAULT_PARENT_FOLDER_ID=                 # Default parent folder
```

## Usage

### Quick Start

```python
from src.client import DriveClient

client = DriveClient()

# Search across all drives including Shared Drives
result = client.search_shared_drive("[20] Build", file_type="folder")
for file in result.files:
    print(f"{file.name}: {file.web_view_link}")

# Create folder in Shared Drive
result = client.create_folder_shared_drive(
    "[47] Build",
    parent_id="parent_folder_id"
)
print(f"Created: {result.web_view_link}")

# List folder contents
contents = client.list_folder("folder_id")
for item in contents.files:
    print(f"{'[folder]' if item.is_folder else '[file]'} {item.name}")
```

## Key Operations

| Operation | Method | Notes |
|-----------|--------|-------|
| Search all drives | `client.search_shared_drive()` | Full Drive access |
| Create folder | `client.create_folder_shared_drive()` | Supports Shared Drives |
| List folder | `client.list_folder()` | Returns files and subfolders |
| Share file | `client.share()` | Set role: reader/writer/commenter |
| Get URL by ID | `client.get_url_by_id()` | No API call needed |
| Delete file | `client.delete()` | Moves to trash |

## Development Guidelines

### Code Style
- Use dataclasses for result types
- Return structured results, not raw API responses
- Include type hints for all functions
- Handle errors gracefully with informative messages

### Testing
```bash
# Run all tests
python scripts/test_all_features.py

# Test connection only
python tests/test_connection.py
```

### Adding New Operations
1. Add function to appropriate module in `src/drive/`
2. Create result dataclass if needed
3. Export from `src/drive/__init__.py`
4. Add convenience method to `DriveClient` in `src/client.py`
5. Add test coverage

## Troubleshooting

### "File not found" for visible files
- Ensure you're using direct Google API methods (not Arcade methods)
- Verify the Shared Drive ID is correct
- Check that your OAuth token has the `drive` scope

### OAuth token issues
- Delete `token.json` and re-authenticate
- Verify `credentials.json` is valid
- Ensure redirect URI matches in Google Cloud Console

### Shared Drive access denied
- Verify you have access to the Shared Drive
- Check that your Google account is added as a member
- Ensure the OAuth consent screen includes your email as a test user
