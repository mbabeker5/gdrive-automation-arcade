#!/usr/bin/env python3
"""Test SearchFiles and CreateFolder in Shared Drives."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.auth import execute_tool

print("=" * 60)
print("Test 1: Search for all files/folders")
print("=" * 60)

try:
    result = execute_tool(
        "GoogleDrive.SearchFiles",
        query="*",
        page_size=20
    )
    print(f"Search result type: {type(result)}")
    if isinstance(result, list):
        print(f"Found {len(result)} items:")
        for item in result[:10]:
            name = item.get('name', 'unknown')
            mime = item.get('mimeType', '')
            file_id = item.get('id', '')
            is_folder = 'folder' in mime
            print(f"  - [{'folder' if is_folder else 'file'}] {name} (ID: {file_id[:20]}...)")
    else:
        print(f"Result: {result}")
except Exception as e:
    print(f"Search error: {e}")

print("\n" + "=" * 60)
print("Test 2: Search specifically for shared drive content")
print("=" * 60)

try:
    # Try searching with includeItemsFromAllDrives parameter
    result = execute_tool(
        "GoogleDrive.SearchFiles",
        query="*",
        include_shared_drives=True,
        page_size=20
    )
    if isinstance(result, list):
        print(f"Found {len(result)} items with shared drives included")
        for item in result[:10]:
            name = item.get('name', 'unknown')
            drive_id = item.get('driveId', 'My Drive')
            print(f"  - {name} (Drive: {drive_id})")
    else:
        print(f"Result: {result}")
except Exception as e:
    print(f"Shared drive search error: {e}")

print("\n" + "=" * 60)
print("Test 3: Create a test folder")
print("=" * 60)

try:
    result = execute_tool(
        "GoogleDrive.CreateFolder",
        folder_name="TestFolder_FromArcade"
    )
    print(f"CreateFolder result: {result}")
    if isinstance(result, dict):
        folder_id = result.get('id', '')
        folder_url = result.get('webViewLink', '')
        print(f"  Folder ID: {folder_id}")
        print(f"  Folder URL: {folder_url}")
except Exception as e:
    print(f"CreateFolder error: {e}")

print("\n" + "=" * 60)
print("Test 4: Search for the folder we just created")
print("=" * 60)

try:
    result = execute_tool(
        "GoogleDrive.SearchFiles",
        query="TestFolder_FromArcade"
    )
    if isinstance(result, list):
        print(f"Found {len(result)} matching items:")
        for item in result:
            print(f"  - {item.get('name')} (ID: {item.get('id')})")
    else:
        print(f"Result: {result}")
except Exception as e:
    print(f"Search error: {e}")
