#!/usr/bin/env python3
"""List shared drives and search for folders."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.client import DriveClient
from src.auth import execute_tool

client = DriveClient()

# Try to get shared drives info
print("Fetching Shared Drives...")
try:
    result = execute_tool("GoogleDrive.ListSharedDrives")
    print(f"Result: {result}")
except Exception as e:
    print(f"ListSharedDrives error: {e}")

# Also try a broader search
print("\n\nSearching for any folder with 'Build' in name...")
results = client.search("Build", file_type="folder")
print(f"Found {len(results.files)} folders:")
for f in results.files[:10]:  # Show first 10
    print(f"  - {f.name} (ID: {f.id})")
