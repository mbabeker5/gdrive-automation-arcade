#!/usr/bin/env python3
"""
Batch create folders in Google Drive.

Creates multiple folders from a list, optionally sharing them with users.

Usage:
    python scripts/batch_create_folders.py folders.txt --share user@example.com
    python scripts/batch_create_folders.py folders.txt --parent FOLDER_ID
    python scripts/batch_create_folders.py folders.txt --output results.csv

Input file format (one folder name per line):
    Project Alpha
    Project Beta
    Reports/2024/Q1
"""

import argparse
import csv
import sys
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.client import DriveClient


def read_folder_names(file_path: str) -> list[str]:
    """Read folder names from a file.

    Args:
        file_path: Path to the input file.

    Returns:
        List of folder names.
    """
    names = []
    with open(file_path, "r") as f:
        for line in f:
            name = line.strip()
            if name and not name.startswith("#"):  # Skip empty lines and comments
                names.append(name)
    return names


def create_folders_batch(
    client: DriveClient,
    folder_names: list[str],
    parent_id: Optional[str] = None,
    share_with: Optional[list[str]] = None,
    role: str = "reader",
    output_file: Optional[str] = None,
) -> tuple[int, int]:
    """Create multiple folders.

    Args:
        client: DriveClient instance.
        folder_names: List of folder names to create.
        parent_id: Optional parent folder ID.
        share_with: Optional list of emails to share with.
        role: Permission role for sharing.
        output_file: Optional CSV file to write results.

    Returns:
        Tuple of (success_count, failure_count).
    """
    results = []
    success_count = 0
    failure_count = 0

    total = len(folder_names)
    print(f"\nCreating {total} folder(s)...")
    print("-" * 60)

    for i, name in enumerate(folder_names, 1):
        print(f"[{i}/{total}] Creating: {name}...", end=" ", flush=True)

        # Check if it's a nested path
        if "/" in name:
            result = client.create_nested_folders(name, root_parent_id=parent_id)
        else:
            if share_with:
                result = client.create_folder_and_share(
                    name,
                    emails=share_with,
                    parent_id=parent_id,
                    role=role,
                )
            else:
                result = client.create_folder(name, parent_id=parent_id)

        if result.success:
            print(f"OK")
            success_count += 1
            results.append({
                "name": name,
                "status": "success",
                "folder_id": result.folder_id,
                "folder_url": result.folder_url,
                "message": result.message,
            })
        else:
            print(f"FAILED: {result.message}")
            failure_count += 1
            results.append({
                "name": name,
                "status": "failed",
                "folder_id": "",
                "folder_url": "",
                "message": result.message,
            })

    # Write results to CSV if requested
    if output_file:
        print(f"\nWriting results to {output_file}...")
        with open(output_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "status", "folder_id", "folder_url", "message"])
            writer.writeheader()
            writer.writerows(results)
        print(f"Results saved to {output_file}")

    return success_count, failure_count


def main():
    parser = argparse.ArgumentParser(
        description="Batch create folders in Google Drive",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Create folders from a file
    python batch_create_folders.py folders.txt

    # Create folders in a specific parent
    python batch_create_folders.py folders.txt --parent 1ABC123...

    # Create and share folders
    python batch_create_folders.py folders.txt --share user1@example.com user2@example.com

    # Save results to CSV
    python batch_create_folders.py folders.txt --output results.csv
        """,
    )

    parser.add_argument(
        "input_file",
        help="File containing folder names (one per line)",
    )
    parser.add_argument(
        "--parent", "-p",
        help="Parent folder ID to create folders in",
    )
    parser.add_argument(
        "--share", "-s",
        nargs="+",
        help="Email addresses to share folders with",
    )
    parser.add_argument(
        "--role", "-r",
        choices=["reader", "writer", "commenter"],
        default="reader",
        help="Permission role for sharing (default: reader)",
    )
    parser.add_argument(
        "--output", "-o",
        help="Output CSV file for results",
    )

    args = parser.parse_args()

    # Read folder names
    if not Path(args.input_file).exists():
        print(f"Error: Input file not found: {args.input_file}")
        sys.exit(1)

    folder_names = read_folder_names(args.input_file)
    if not folder_names:
        print("Error: No folder names found in input file")
        sys.exit(1)

    print(f"Found {len(folder_names)} folder name(s) in {args.input_file}")

    # Create client
    try:
        client = DriveClient()
    except Exception as e:
        print(f"Error: Could not create client: {e}")
        print("Please ensure your .env file is configured correctly")
        sys.exit(1)

    # Create folders
    success, failed = create_folders_batch(
        client,
        folder_names,
        parent_id=args.parent,
        share_with=args.share,
        role=args.role,
        output_file=args.output,
    )

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Total:   {len(folder_names)}")
    print(f"Success: {success}")
    print(f"Failed:  {failed}")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
