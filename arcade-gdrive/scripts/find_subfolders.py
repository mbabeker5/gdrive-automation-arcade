#!/usr/bin/env python3
"""Find subfolders under a specific folder."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.client import DriveClient

client = DriveClient()

# First find the [20] Build folder
results = client.search("[20] Build")
print("Search results for '[20] Build':")
for f in results.files:
    print(f"  - {f.name} (ID: {f.id}, folder: {f.is_folder})")

# If we found it, search within it
if results.files:
    folder = results.files[0]
    print(f"\nSearching for contents inside '{folder.name}' (ID: {folder.id})...")

    # Search with parent_id
    contents = client.search("*", parent_id=folder.id)
    print(f"\nFound {len(contents.files)} items:")
    for f in contents.files:
        file_type = "folder" if f.is_folder else "file"
        print(f"  - [{file_type}] {f.name}")
else:
    print("\nNo folder found matching '[20] Build'")
