#!/usr/bin/env python3
"""Check available Arcade tools."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.auth import get_arcade_client

client = get_arcade_client()

# List available tools
print("Fetching available GoogleDrive tools...")
try:
    tools = client.tools.list()
    gdrive_tools = [t for t in tools if 'Google' in str(t.name)]
    print(f"\nFound {len(gdrive_tools)} Google-related tools:")
    for tool in gdrive_tools:
        print(f"  - {tool.name}")
except Exception as e:
    print(f"Error listing tools: {e}")
