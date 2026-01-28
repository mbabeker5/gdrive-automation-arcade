#!/usr/bin/env python3
"""
Prepare environment variables for deployment.

This script reads your local token.json and outputs the environment
variables needed for Railway/Render deployment.

Usage:
    python scripts/prepare_deploy.py

Then copy the output to your deployment platform's environment variables.
"""

import json
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    project_root = Path(__file__).parent.parent
    token_path = project_root / "token.json"

    print("=" * 60)
    print("Deployment Environment Variables")
    print("=" * 60)
    print()

    # Check token.json
    if not token_path.exists():
        print("ERROR: token.json not found!")
        print("Please run the app locally first to authenticate.")
        sys.exit(1)

    with open(token_path) as f:
        token_data = json.load(f)

    # Convert to single-line JSON for env var
    token_json = json.dumps(token_data)

    print("Set these environment variables in Railway/Render:\n")
    print("-" * 60)

    # Required
    print("# REQUIRED - Google OAuth Token (from token.json)")
    print(f"GOOGLE_TOKEN_JSON={token_json}")
    print()

    # Anthropic API Key
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    if anthropic_key:
        print("# REQUIRED - Anthropic API Key")
        print(f"ANTHROPIC_API_KEY={anthropic_key}")
    else:
        print("# REQUIRED - Anthropic API Key (get from .env)")
        print("ANTHROPIC_API_KEY=<your-anthropic-api-key>")
    print()

    print("-" * 60)
    print()
    print("IMPORTANT NOTES:")
    print("1. The GOOGLE_TOKEN_JSON contains your refresh token")
    print("2. It will auto-refresh, but if it expires, re-run locally")
    print("3. Keep these values SECRET - never commit to git")
    print()
    print("Railway deployment:")
    print("  1. Push code to GitHub (private repo)")
    print("  2. Connect Railway to your repo")
    print("  3. Add the environment variables above")
    print("  4. Railway will auto-deploy")


if __name__ == "__main__":
    main()
