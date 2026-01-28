#!/usr/bin/env python3
"""
Test script for full Shared Drive access.

This script verifies that the full Drive scope is working correctly by:
1. Searching for '[20] Build' folder in Shared Drives
2. Listing its contents (both files AND folders)
3. Creating a test folder in a Shared Drive
4. Deleting the test folder

Run this script directly in your terminal (not in Claude's sandbox):
    cd "/Users/MTalib/workspace_repos/Gdrive Automation/arcade-gdrive"
    source venv/bin/activate
    python scripts/test_shared_drive_full.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.client import DriveClient


def separator(title: str) -> None:
    """Print a section separator."""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def test_search_shared_drive(client: DriveClient) -> Optional[str]:
    """Test 1: Search for [20] Build folder."""
    separator("Test 1: Search for '[20] Build' folder")

    result = client.search_shared_drive("[20] Build", file_type="folder")

    if not result.success:
        print(f"FAILED: {result.error}")
        return None

    print(f"Found {result.count} matching folders:")
    folder_id = None

    for f in result.files:
        print(f"\n  - {f.name}")
        print(f"    ID: {f.id}")
        print(f"    URL: {f.web_view_link}")
        print(f"    Shared Drive: {f.drive_id or 'My Drive'}")

        if "[20] Build" in f.name and folder_id is None:
            folder_id = f.id

    if folder_id:
        print(f"\nSUCCESS: Found folder, ID: {folder_id}")
    else:
        print("\nWARNING: No exact match found")

    return folder_id


def test_list_folder_contents(client: DriveClient, folder_id: str) -> None:
    """Test 2: List contents of the folder."""
    separator(f"Test 2: List contents of folder {folder_id}")

    result = client.list_folder(folder_id)

    if not result.success:
        print(f"FAILED: {result.error}")
        return

    print(f"Folder: {result.folder_name}")
    print(f"Items: {result.count}")

    folders = [f for f in result.files if f.is_folder]
    files = [f for f in result.files if not f.is_folder]

    print(f"\nFolders ({len(folders)}):")
    for f in folders:
        print(f"  [folder] {f.name}")

    print(f"\nFiles ({len(files)}):")
    for f in files:
        print(f"  [file] {f.name}")

    print("\nSUCCESS: Listed folder contents")


def test_create_folder_shared_drive(client: DriveClient, parent_id: str) -> Optional[str]:
    """Test 3: Create a test folder in Shared Drive."""
    separator("Test 3: Create test folder in Shared Drive")

    test_folder_name = "__TEST_FOLDER_DELETE_ME__"

    result = client.create_folder_shared_drive(test_folder_name, parent_id)

    if not result.success:
        print(f"FAILED: {result.error}")
        return None

    print(f"Created folder: {result.folder_name}")
    print(f"ID: {result.folder_id}")
    print(f"URL: {result.web_view_link}")
    print("\nSUCCESS: Folder created in Shared Drive")

    return result.folder_id


def test_delete_folder(client: DriveClient, folder_id: str) -> None:
    """Test 4: Delete the test folder."""
    separator("Test 4: Delete test folder")

    success = client.delete(folder_id)

    if success:
        print(f"Deleted folder: {folder_id}")
        print("\nSUCCESS: Folder deleted")
    else:
        print(f"FAILED: Could not delete folder {folder_id}")


def test_list_shared_drives(client: DriveClient) -> None:
    """Bonus: List all accessible Shared Drives."""
    separator("Bonus: List all Shared Drives")

    drives = client.get_all_shared_drives()

    if not drives:
        print("No Shared Drives found (or error occurred)")
        return

    print(f"Found {len(drives)} Shared Drives:")
    for d in drives:
        print(f"  - {d.name}")
        print(f"    ID: {d.id}")


def main():
    print("=" * 60)
    print("Full Shared Drive Access Test")
    print("=" * 60)
    print("\nThis test verifies full Drive access with these operations:")
    print("  1. Search for folders in Shared Drive")
    print("  2. List folder contents (files AND folders)")
    print("  3. Create folder in Shared Drive")
    print("  4. Delete folder")

    # Initialize client
    print("\nInitializing client...")
    client = DriveClient()
    print(f"User: {client.user_id}")

    # Run tests
    all_passed = True

    # Test 1: Search
    folder_id = test_search_shared_drive(client)
    if not folder_id:
        print("\nCannot continue without finding a folder.")
        print("Make sure '[20] Build' exists in your Shared Drive.")
        return

    # Test 2: List contents
    test_list_folder_contents(client, folder_id)

    # Test 3: Create folder
    test_folder_id = test_create_folder_shared_drive(client, folder_id)

    # Test 4: Delete folder (only if we created one)
    if test_folder_id:
        test_delete_folder(client, test_folder_id)
    else:
        all_passed = False

    # Bonus: List Shared Drives
    test_list_shared_drives(client)

    # Summary
    separator("Test Summary")
    if all_passed:
        print("All tests PASSED!")
        print("\nFull Shared Drive access is working correctly.")
        print("You can now use:")
        print("  - client.search_shared_drive() to find files in Shared Drives")
        print("  - client.list_folder() to list folder contents")
        print("  - client.create_folder_shared_drive() to create folders")
    else:
        print("Some tests FAILED. Check the output above for details.")


if __name__ == "__main__":
    main()
