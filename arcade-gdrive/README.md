# Google Drive Automation Toolkit

Python library for automating Google Drive operations, designed for professional services project management workflows.

## Features

- **Search** files and folders across My Drive and Shared Drives
- **Create** folders with nested structure support
- **Share** files/folders with customizable permissions
- **Move** and rename files between folders
- **Download** files with chunked download support for large files
- **Upload** files from URLs

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/arcade-gdrive.git
cd arcade-gdrive

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Authentication Setup

### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the **Google Drive API**
4. Configure OAuth consent screen:
   - Select "External" user type
   - Add scopes: `drive`, `drive.metadata.readonly`
   - Add your email as a test user

### 2. Create OAuth Credentials

1. Go to **APIs & Services > Credentials**
2. Click **Create Credentials > OAuth client ID**
3. Select **Desktop application**
4. Download the JSON file as `credentials.json`
5. Place `credentials.json` in the project root

### 3. Configure Environment

Create a `.env` file:

```bash
GOOGLE_CREDENTIALS_FILE=credentials.json
GOOGLE_TOKEN_FILE=token.json

# Optional: Default Shared Drive
DEFAULT_SHARED_DRIVE_ID=your_shared_drive_id
```

### 4. Authenticate

Run the test connection script to complete OAuth:

```bash
python tests/test_connection.py
```

This will open a browser for Google sign-in. After authorization, `token.json` will be created.

## Quick Start

```python
from src.client import DriveClient

# Initialize client
client = DriveClient()

# Search for folders
result = client.search_shared_drive("[20] Build", file_type="folder")
for file in result.files:
    print(f"{file.name}: {file.web_view_link}")

# Create a folder
result = client.create_folder_shared_drive(
    name="[47] Build",
    parent_id="parent_folder_id"
)
print(f"Created folder: {result.web_view_link}")

# Share with a user
client.share(
    file_id="folder_id",
    emails=["contractor@example.com"],
    role="writer"  # reader, writer, or commenter
)

# List folder contents
contents = client.list_folder("folder_id")
for item in contents.files:
    kind = "folder" if item.is_folder else "file"
    print(f"[{kind}] {item.name}")
```

## Use Cases

### Project Management

Create organized folder structures for multiple projects:

```python
from src.client import DriveClient

client = DriveClient()
parent_id = "your_parent_folder_id"

# Create folders for projects 47-52
for project_id in range(47, 53):
    result = client.create_folder_shared_drive(
        name=f"[{project_id}] Build",
        parent_id=parent_id
    )
    print(f"Project {project_id}: {result.web_view_link}")
```

### Contractor Onboarding

Share multiple folders with a new contractor:

```python
folder_ids = ["id1", "id2", "id3"]
contractor_email = "contractor@example.com"

for folder_id in folder_ids:
    client.share(
        file_id=folder_id,
        emails=[contractor_email],
        role="writer",
        send_notification=True,
        message="Here's your project folder"
    )
```

### Batch URL Export

Get shareable URLs for multiple folders:

```python
folder_names = ["[20] Build", "[25] Build", "[31] Build"]

for name in folder_names:
    result = client.search_shared_drive(name, file_type="folder")
    if result.files:
        folder = result.files[0]
        print(f"{name}\t{folder.web_view_link}")
```

## API Reference

### DriveClient Methods

| Method | Description |
|--------|-------------|
| `search_shared_drive(query, file_type=None)` | Search across all drives |
| `create_folder_shared_drive(name, parent_id)` | Create folder in Shared Drive |
| `list_folder(folder_id)` | List folder contents |
| `share(file_id, emails, role)` | Share with users |
| `download(file_id, output_path)` | Download file to disk |
| `rename(file_id, new_name)` | Rename file/folder |
| `move(file_id, new_parent_id)` | Move to different folder |
| `delete(file_id)` | Move to trash |
| `get_url_by_id(file_id, is_folder)` | Get Drive URL (no API call) |
| `get_all_shared_drives()` | List accessible Shared Drives |

### Permission Roles

| Role | Capabilities |
|------|--------------|
| `reader` | View only |
| `commenter` | View and comment |
| `writer` | View, comment, and edit |

## Batch Scripts

Pre-built scripts for common workflows:

```bash
# Create multiple project folders
python scripts/batch_create_folders.py

# Get URLs for existing folders
python scripts/batch_get_urls.py
```

## Limitations

- **Rate Limits**: Google Drive API has quota limits. For bulk operations, implement delays between requests.
- **File Size**: Large file downloads use chunked transfer. Very large files may require additional handling.
- **Permissions**: Operations on Shared Drives require appropriate membership permissions.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `python scripts/test_all_features.py`
5. Submit a pull request

## License

MIT License - see LICENSE file for details.
