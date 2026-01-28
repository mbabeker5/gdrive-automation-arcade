#!/usr/bin/env python3
"""Generate a file picker URL to grant access to folders."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.auth import execute_tool

print("Generating Google File Picker URL...")
print("This will let you select a folder to grant access to.\n")

try:
    result = execute_tool("GoogleDrive.GenerateGoogleFilePickerUrl")
    print(f"File Picker URL: {result}")
    print("\nOpen this URL, select your Shared Drive or the [20] Build folder,")
    print("and the app will be granted access to it.")
except Exception as e:
    print(f"Error: {e}")
