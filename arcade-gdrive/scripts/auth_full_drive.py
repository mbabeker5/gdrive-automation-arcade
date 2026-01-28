#!/usr/bin/env python3
"""
Authorize with full Google Drive scope and search for folders.

This uses client.auth.start() to request the full 'drive' scope,
which gives access to ALL files (not just app-created files).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from arcadepy import Arcade
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv
import os

load_dotenv(Path(__file__).parent.parent / '.env')

client = Arcade(api_key=os.getenv("ARCADE_API_KEY"))
user_id = os.getenv("ARCADE_USER_ID")

print("=" * 60, flush=True)
print("Requesting FULL Google Drive access (auth/drive scope)", flush=True)
print("=" * 60, flush=True)

print(f"User ID: {user_id}", flush=True)

# Start authorization with full drive scope
print("Calling client.auth.start()...", flush=True)
try:
    auth_response = client.auth.start(
        user_id=user_id,
        provider="google",
        scopes=[
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
        ],
    )
    print(f"auth.start() returned: status={auth_response.status}", flush=True)
except Exception as e:
    print(f"ERROR in auth.start(): {e}", flush=True)
    sys.exit(1)

if auth_response.status != "completed":
    print("\nPlease complete the authorization in your browser:", flush=True)
    print(auth_response.url, flush=True)
    print("\nWaiting for authorization...", flush=True)
    auth_response = client.auth.wait_for_completion(auth_response)

print(f"\nAuth status: {auth_response.status}")

if auth_response.status != "completed":
    print("Authorization failed!")
    sys.exit(1)

token = auth_response.context.token
if not token:
    print("No token received!")
    sys.exit(1)

print("Authorization successful! Got token.")

# Now use the Google Drive API directly
print("\n" + "=" * 60)
print("Searching for '[20] Build' folder using Google Drive API")
print("=" * 60)

credentials = Credentials(token)
drive_service = build("drive", "v3", credentials=credentials)

# Search for the folder
query = "name contains '[20] Build' and mimeType = 'application/vnd.google-apps.folder'"
results = drive_service.files().list(
    q=query,
    spaces="drive",
    includeItemsFromAllDrives=True,
    supportsAllDrives=True,
    fields="files(id, name, parents, webViewLink, driveId)"
).execute()

files = results.get("files", [])
print(f"\nFound {len(files)} matching folders:")
for f in files:
    print(f"  - {f.get('name')}")
    print(f"    ID: {f.get('id')}")
    print(f"    URL: {f.get('webViewLink')}")
    print(f"    Drive ID: {f.get('driveId', 'My Drive')}")
    print()

if files:
    # Get contents of the first matching folder
    folder = files[0]
    folder_id = folder.get("id")
    print("=" * 60)
    print(f"Contents of '{folder.get('name')}':")
    print("=" * 60)

    contents_query = f"'{folder_id}' in parents and trashed = false"
    contents = drive_service.files().list(
        q=contents_query,
        includeItemsFromAllDrives=True,
        supportsAllDrives=True,
        fields="files(id, name, mimeType, webViewLink)"
    ).execute()

    content_files = contents.get("files", [])
    print(f"\nFound {len(content_files)} items:")
    for f in content_files:
        is_folder = f.get("mimeType") == "application/vnd.google-apps.folder"
        print(f"  - [{'folder' if is_folder else 'file'}] {f.get('name')}")
