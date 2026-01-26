#!/usr/bin/env python3
"""
Test script to verify Arcade connection and Google Drive access.

Run this after setting up your .env file to verify everything is working.

Usage:
    python tests/test_connection.py
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import load_dotenv_if_exists, get_config
from src.client import DriveClient


def test_config():
    """Test that configuration loads correctly."""
    print("=" * 60)
    print("Testing Configuration")
    print("=" * 60)

    try:
        load_dotenv_if_exists()
        config = get_config()
        print(f"[OK] API Key loaded: {'*' * 8}{config.arcade_api_key[-4:]}")
        print(f"[OK] User ID: {config.arcade_user_id}")

        if config.default_parent_folder_id:
            print(f"[OK] Default parent folder: {config.default_parent_folder_id}")
        else:
            print("[INFO] No default parent folder configured")

        if config.default_shared_drive_id:
            print(f"[OK] Default shared drive: {config.default_shared_drive_id}")
        else:
            print("[INFO] No default shared drive configured")

        return True
    except ValueError as e:
        print(f"[FAIL] Configuration error: {e}")
        return False


def test_client_creation():
    """Test that the client can be created."""
    print("\n" + "=" * 60)
    print("Testing Client Creation")
    print("=" * 60)

    try:
        client = DriveClient()
        print(f"[OK] Client created for user: {client.user_id}")
        return client
    except Exception as e:
        print(f"[FAIL] Could not create client: {e}")
        return None


def test_user_info(client: DriveClient):
    """Test getting user info from Google."""
    print("\n" + "=" * 60)
    print("Testing User Info Retrieval")
    print("=" * 60)

    try:
        info = client.get_user_info()

        if "error" in info:
            print(f"[WARN] Could not get user info: {info['error']}")
            print("[INFO] This may be expected if GetUserInfo tool is not available")
            return True  # Not a critical failure

        email = info.get("email", info.get("emailAddress", "unknown"))
        name = info.get("name", info.get("displayName", "unknown"))

        print(f"[OK] Authenticated as: {name}")
        print(f"[OK] Email: {email}")
        return True
    except Exception as e:
        print(f"[WARN] Error getting user info: {e}")
        return True  # Not critical


def test_list_shared_drives(client: DriveClient):
    """Test listing Shared Drives."""
    print("\n" + "=" * 60)
    print("Testing Shared Drives Access")
    print("=" * 60)

    try:
        result = client.list_shared_drives()

        if result.success:
            print(f"[OK] Found {result.total_count} Shared Drive(s)")
            for drive in result.files[:5]:  # Show first 5
                print(f"     - {drive.name} ({drive.id})")
            if result.total_count > 5:
                print(f"     ... and {result.total_count - 5} more")
            return True
        else:
            print(f"[WARN] Could not list Shared Drives: {result.message}")
            print("[INFO] This may be expected if you don't have Shared Drives")
            return True  # Not critical
    except Exception as e:
        print(f"[WARN] Error listing Shared Drives: {e}")
        return True


def test_search(client: DriveClient):
    """Test basic search functionality."""
    print("\n" + "=" * 60)
    print("Testing Search")
    print("=" * 60)

    try:
        # Search for any file
        result = client.search("*", max_results=5)

        if result.success:
            print(f"[OK] Search returned {result.total_count} result(s)")
            for file in result.files[:3]:
                file_type = "folder" if file.is_folder else "file"
                print(f"     - [{file_type}] {file.name}")
            return True
        else:
            print(f"[FAIL] Search failed: {result.message}")
            return False
    except Exception as e:
        print(f"[FAIL] Search error: {e}")
        return False


def test_url_construction(client: DriveClient):
    """Test URL construction utilities."""
    print("\n" + "=" * 60)
    print("Testing URL Utilities")
    print("=" * 60)

    test_id = "1234567890abcdefg"

    try:
        # Test file URL
        file_url = client.build_url(test_id, is_folder=False)
        expected_file = f"https://drive.google.com/file/d/{test_id}/view"
        assert file_url == expected_file, f"Expected {expected_file}, got {file_url}"
        print(f"[OK] File URL: {file_url}")

        # Test folder URL
        folder_url = client.build_url(test_id, is_folder=True)
        expected_folder = f"https://drive.google.com/drive/folders/{test_id}"
        assert folder_url == expected_folder, f"Expected {expected_folder}, got {folder_url}"
        print(f"[OK] Folder URL: {folder_url}")

        # Test parsing
        parsed = client.parse_file_id(file_url)
        assert parsed == test_id, f"Expected {test_id}, got {parsed}"
        print(f"[OK] Parsed ID from URL: {parsed}")

        return True
    except AssertionError as e:
        print(f"[FAIL] Assertion failed: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] URL utility error: {e}")
        return False


def main():
    """Run all tests."""
    print("\nArcade Google Drive Connection Test")
    print("=" * 60)

    results = []

    # Test 1: Configuration
    results.append(("Configuration", test_config()))

    if not results[-1][1]:
        print("\n[ABORT] Cannot continue without valid configuration")
        print("\nPlease ensure you have:")
        print("1. Created a .env file (copy from .env.example)")
        print("2. Set ARCADE_API_KEY to your Arcade API key")
        print("3. Set ARCADE_USER_ID to your email address")
        sys.exit(1)

    # Test 2: Client Creation
    client = test_client_creation()
    results.append(("Client Creation", client is not None))

    if not client:
        print("\n[ABORT] Cannot continue without a working client")
        sys.exit(1)

    # Test 3: User Info
    results.append(("User Info", test_user_info(client)))

    # Test 4: Shared Drives
    results.append(("Shared Drives", test_list_shared_drives(client)))

    # Test 5: Search
    results.append(("Search", test_search(client)))

    # Test 6: URL Utilities
    results.append(("URL Utilities", test_url_construction(client)))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = 0
    failed = 0
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {name}")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\nTotal: {passed} passed, {failed} failed")

    if failed == 0:
        print("\n[SUCCESS] All tests passed! Your setup is working correctly.")
        print("\nYou can now use the toolkit:")
        print("  from src.client import DriveClient")
        print("  client = DriveClient()")
        print("  results = client.search('your query')")
    else:
        print("\n[WARNING] Some tests failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
