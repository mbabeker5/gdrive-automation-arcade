#!/usr/bin/env python3
"""Force re-authorization with new scopes."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.auth import reset_client, authorize_tool

# Reset the client and auth cache
reset_client()
print("Auth cache cleared.")

print("\nAttempting to authorize GoogleDrive.SearchFiles...")
print("This should trigger a new OAuth flow with updated scopes.\n")

try:
    authorize_tool("GoogleDrive.SearchFiles")
    print("\nAuthorization successful!")
except Exception as e:
    print(f"\nError: {e}")
