#!/usr/bin/env python3
"""
Batch get URLs for Google Drive files or folders.

Searches for items by name and returns their URLs.

Usage:
    python scripts/batch_get_urls.py names.txt --output urls.csv
    python scripts/batch_get_urls.py names.txt --folders-only
    python scripts/batch_get_urls.py --ids ids.txt --output urls.csv

Input file format (one name or ID per line):
    Project Alpha
    Quarterly Report
    Meeting Notes
"""

import argparse
import csv
import sys
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.client import DriveClient


def read_items(file_path: str) -> list[str]:
    """Read item names or IDs from a file.

    Args:
        file_path: Path to the input file.

    Returns:
        List of names or IDs.
    """
    items = []
    with open(file_path, "r") as f:
        for line in f:
            item = line.strip()
            if item and not item.startswith("#"):
                items.append(item)
    return items


def get_urls_by_name(
    client: DriveClient,
    names: list[str],
    folders_only: bool = False,
    exact_match: bool = True,
) -> list[dict]:
    """Get URLs by searching for items by name.

    Args:
        client: DriveClient instance.
        names: List of names to search for.
        folders_only: Only return folders.
        exact_match: Require exact name match.

    Returns:
        List of result dictionaries.
    """
    results = []
    total = len(names)

    print(f"\nSearching for {total} item(s)...")
    print("-" * 60)

    for i, name in enumerate(names, 1):
        print(f"[{i}/{total}] Searching: {name}...", end=" ", flush=True)

        file_type = "folder" if folders_only else None
        search_result = client.find_by_name(name, exact_match=exact_match, file_type=file_type)

        if search_result.success and search_result.files:
            # Take the first match
            file = search_result.files[0]
            print(f"Found ({file.mime_type})")
            results.append({
                "name": name,
                "status": "found",
                "file_id": file.id,
                "url": file.url,
                "found_name": file.name,
                "is_folder": str(file.is_folder),
            })

            if len(search_result.files) > 1:
                print(f"         (Note: {len(search_result.files)} matches found, using first)")
        else:
            print("Not found")
            results.append({
                "name": name,
                "status": "not_found",
                "file_id": "",
                "url": "",
                "found_name": "",
                "is_folder": "",
            })

    return results


def get_urls_by_id(
    client: DriveClient,
    file_ids: list[str],
    assume_folders: bool = False,
) -> list[dict]:
    """Get URLs for known file IDs.

    Args:
        client: DriveClient instance.
        file_ids: List of file IDs.
        assume_folders: Assume all IDs are folders.

    Returns:
        List of result dictionaries.
    """
    results = []
    total = len(file_ids)

    print(f"\nGenerating URLs for {total} ID(s)...")
    print("-" * 60)

    for i, file_id in enumerate(file_ids, 1):
        print(f"[{i}/{total}] {file_id[:20]}...", end=" ", flush=True)

        try:
            url = client.get_url_by_id(file_id, is_folder=assume_folders)
            print("OK")
            results.append({
                "file_id": file_id,
                "status": "success",
                "url": url,
                "is_folder": str(assume_folders),
            })
        except Exception as e:
            print(f"Error: {e}")
            results.append({
                "file_id": file_id,
                "status": "error",
                "url": "",
                "is_folder": "",
            })

    return results


def write_results(results: list[dict], output_file: str) -> None:
    """Write results to a CSV file.

    Args:
        results: List of result dictionaries.
        output_file: Output file path.
    """
    if not results:
        print("No results to write")
        return

    fieldnames = results[0].keys()
    with open(output_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\nResults saved to {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Batch get URLs for Google Drive files or folders",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Search by name
    python batch_get_urls.py names.txt --output urls.csv

    # Search for folders only
    python batch_get_urls.py names.txt --folders-only

    # Get URLs for known IDs (no API calls)
    python batch_get_urls.py --ids ids.txt --output urls.csv

    # Get folder URLs for known IDs
    python batch_get_urls.py --ids ids.txt --folders-only
        """,
    )

    parser.add_argument(
        "input_file",
        nargs="?",
        help="File containing names to search for (one per line)",
    )
    parser.add_argument(
        "--ids",
        help="File containing file IDs (constructs URLs directly, no search)",
    )
    parser.add_argument(
        "--output", "-o",
        help="Output CSV file for results",
    )
    parser.add_argument(
        "--folders-only", "-f",
        action="store_true",
        help="Only search for folders / assume IDs are folders",
    )
    parser.add_argument(
        "--partial-match",
        action="store_true",
        help="Allow partial name matches (default: exact match)",
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.input_file and not args.ids:
        parser.error("Either input_file or --ids must be provided")

    # Create client
    try:
        client = DriveClient()
    except Exception as e:
        print(f"Error: Could not create client: {e}")
        print("Please ensure your .env file is configured correctly")
        sys.exit(1)

    results = []

    if args.ids:
        # Get URLs by ID (no search needed)
        ids_file = args.ids
        if not Path(ids_file).exists():
            print(f"Error: IDs file not found: {ids_file}")
            sys.exit(1)

        file_ids = read_items(ids_file)
        if not file_ids:
            print("Error: No file IDs found in input file")
            sys.exit(1)

        print(f"Found {len(file_ids)} file ID(s) in {ids_file}")
        results = get_urls_by_id(client, file_ids, assume_folders=args.folders_only)

    else:
        # Search by name
        if not Path(args.input_file).exists():
            print(f"Error: Input file not found: {args.input_file}")
            sys.exit(1)

        names = read_items(args.input_file)
        if not names:
            print("Error: No names found in input file")
            sys.exit(1)

        print(f"Found {len(names)} name(s) in {args.input_file}")
        results = get_urls_by_name(
            client,
            names,
            folders_only=args.folders_only,
            exact_match=not args.partial_match,
        )

    # Output results
    if args.output:
        write_results(results, args.output)
    else:
        # Print to console
        print("\n" + "=" * 60)
        print("Results")
        print("=" * 60)
        for r in results:
            if "name" in r:
                print(f"{r['name']}: {r['url'] or 'Not found'}")
            else:
                print(f"{r['file_id']}: {r['url']}")

    # Summary
    found = sum(1 for r in results if r.get("status") in ("found", "success"))
    not_found = len(results) - found

    print("\n" + "-" * 60)
    print(f"Total:     {len(results)}")
    print(f"Found:     {found}")
    print(f"Not found: {not_found}")


if __name__ == "__main__":
    main()
