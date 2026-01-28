"""
Google Drive sharing operations.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from ..auth import get_drive_service, GoogleAuthError
from .folders import create_folder, FolderResult
from .utils import build_drive_url, validate_file_id

logger = logging.getLogger(__name__)


@dataclass
class ShareResult:
    """Result of a sharing operation."""

    success: bool
    message: str
    # Use field(default_factory=list) to avoid mutable default argument bug
    shared_with: list[str] = field(default_factory=list)
    failed_shares: list[str] = field(default_factory=list)


@dataclass
class UrlResult:
    """Result containing a URL for a file or folder."""

    success: bool
    url: Optional[str]
    file_id: Optional[str]
    message: str
    sharing_status: Optional[ShareResult] = None


def share_with_users(
    file_id: str,
    emails: list[str],
    role: str = "reader",
    send_notification: bool = True,
    message: Optional[str] = None,
) -> ShareResult:
    """Share a file or folder with one or more users.

    Args:
        file_id: The ID of the file or folder to share.
        emails: List of email addresses to share with.
        role: Permission role - "reader", "writer", or "commenter".
        send_notification: Whether to send email notifications.
        message: Optional custom message to include in the notification email.

    Returns:
        ShareResult: Result of the sharing operation.
    """
    # Validate inputs
    try:
        file_id = validate_file_id(file_id)
    except ValueError as e:
        return ShareResult(
            success=False,
            message=str(e),
        )

    if not emails:
        return ShareResult(
            success=False,
            message="At least one email address is required",
        )

    # Validate role
    valid_roles = {"reader", "writer", "commenter"}
    if role not in valid_roles:
        return ShareResult(
            success=False,
            message=f"Invalid role '{role}'. Must be one of: {', '.join(valid_roles)}",
        )

    shared_with: list[str] = []
    failed_shares: list[str] = []

    try:
        service = get_drive_service()
    except GoogleAuthError as e:
        return ShareResult(
            success=False,
            message=str(e),
        )

    for email in emails:
        email = email.strip()
        if not email:
            continue

        try:
            permission = {
                "type": "user",
                "role": role,
                "emailAddress": email,
            }

            kwargs = {
                "fileId": file_id,
                "body": permission,
                "sendNotificationEmail": send_notification,
                "supportsAllDrives": True,
            }
            if message and send_notification:
                kwargs["emailMessage"] = message

            service.permissions().create(**kwargs).execute()

            shared_with.append(email)
            logger.debug(f"Shared with {email}")

        except Exception as e:
            logger.error(f"Failed to share with {email}: {e}")
            failed_shares.append(email)

    # Determine overall success
    if not shared_with and failed_shares:
        return ShareResult(
            success=False,
            message=f"Failed to share with all {len(failed_shares)} user(s)",
            shared_with=shared_with,
            failed_shares=failed_shares,
        )

    if failed_shares:
        return ShareResult(
            success=True,  # Partial success
            message=f"Shared with {len(shared_with)} user(s), failed for {len(failed_shares)}",
            shared_with=shared_with,
            failed_shares=failed_shares,
        )

    return ShareResult(
        success=True,
        message=f"Successfully shared with {len(shared_with)} user(s)",
        shared_with=shared_with,
        failed_shares=failed_shares,
    )


def create_folder_and_share(
    folder_name: str,
    emails: list[str],
    parent_id: Optional[str] = None,
    role: str = "reader",
) -> FolderResult:
    """Create a folder and share it with users.

    Args:
        folder_name: Name for the new folder.
        emails: List of email addresses to share with.
        parent_id: Optional parent folder ID.
        role: Permission role for sharing.

    Returns:
        FolderResult: Result including any sharing failures in the message.
    """
    # First create the folder
    create_result = create_folder(folder_name, parent_id=parent_id)

    if not create_result.success:
        return create_result

    # Don't attempt sharing if no folder ID (should be caught above, but be safe)
    if not create_result.folder_id:
        return FolderResult(
            success=False,
            folder_id=None,
            folder_url=None,
            message="Folder creation returned no ID",
        )

    # Share with users if emails provided
    if emails:
        share_result = share_with_users(
            create_result.folder_id,
            emails,
            role=role,
        )

        # Critical fix: Report sharing failures instead of silently ignoring
        if not share_result.success:
            return FolderResult(
                success=True,  # Folder was created
                folder_id=create_result.folder_id,
                folder_url=create_result.folder_url,
                message=f"Folder created but sharing failed: {share_result.message}",
            )

        if share_result.failed_shares:
            return FolderResult(
                success=True,
                folder_id=create_result.folder_id,
                folder_url=create_result.folder_url,
                message=(
                    f"Folder created, shared with {len(share_result.shared_with)} user(s), "
                    f"failed for: {', '.join(share_result.failed_shares)}"
                ),
            )

    return FolderResult(
        success=True,
        folder_id=create_result.folder_id,
        folder_url=create_result.folder_url,
        message=f"Created folder '{folder_name}' and shared with {len(emails)} user(s)",
    )


def create_folder_and_get_url(
    folder_name: str,
    parent_id: Optional[str] = None,
    share_with: Optional[list[str]] = None,
    role: str = "reader",
) -> UrlResult:
    """Create a folder and return its URL, optionally sharing it.

    This is a convenience function that combines folder creation and sharing,
    and returns just the URL for easy access.

    Args:
        folder_name: Name for the new folder.
        parent_id: Optional parent folder ID.
        share_with: Optional list of email addresses to share with.
        role: Permission role for sharing.

    Returns:
        UrlResult: Result containing the folder URL and sharing status.
    """
    # Create the folder
    create_result = create_folder(folder_name, parent_id=parent_id)

    if not create_result.success:
        return UrlResult(
            success=False,
            url=None,
            file_id=None,
            message=create_result.message,
        )

    if not create_result.folder_id:
        return UrlResult(
            success=False,
            url=None,
            file_id=None,
            message="Folder creation returned no ID",
        )

    # Share if requested
    sharing_status: Optional[ShareResult] = None
    if share_with:
        sharing_status = share_with_users(
            create_result.folder_id,
            share_with,
            role=role,
        )

        # Critical fix: Report sharing result in the response
        if not sharing_status.success:
            return UrlResult(
                success=True,  # Folder was created
                url=create_result.folder_url,
                file_id=create_result.folder_id,
                message=f"Folder created but sharing failed: {sharing_status.message}",
                sharing_status=sharing_status,
            )

    return UrlResult(
        success=True,
        url=create_result.folder_url,
        file_id=create_result.folder_id,
        message=f"Created folder '{folder_name}'",
        sharing_status=sharing_status,
    )


def get_sharing_permissions(file_id: str) -> ShareResult:
    """Get the current sharing permissions for a file or folder.

    Args:
        file_id: The ID of the file or folder.

    Returns:
        ShareResult: Result containing list of users the file is shared with.
    """
    try:
        file_id = validate_file_id(file_id)
    except ValueError as e:
        return ShareResult(
            success=False,
            message=str(e),
        )

    try:
        service = get_drive_service()

        permissions = service.permissions().list(
            fileId=file_id,
            supportsAllDrives=True,
            fields="permissions(id, type, role, emailAddress, displayName)",
        ).execute()

        shared_with = []
        for perm in permissions.get("permissions", []):
            email = perm.get("emailAddress")
            if email:
                shared_with.append(email)

        return ShareResult(
            success=True,
            message=f"Found {len(shared_with)} permission(s)",
            shared_with=shared_with,
        )

    except GoogleAuthError as e:
        logger.error(f"Get sharing permissions failed: {e}")
        return ShareResult(
            success=False,
            message=str(e),
        )
    except Exception as e:
        logger.error(f"Get sharing permissions failed: {e}")
        return ShareResult(
            success=False,
            message=str(e),
        )


def remove_sharing(file_id: str, email: str) -> ShareResult:
    """Remove sharing permission for a specific user.

    Args:
        file_id: The ID of the file or folder.
        email: Email address of the user to remove.

    Returns:
        ShareResult: Result of the removal operation.
    """
    try:
        file_id = validate_file_id(file_id)
    except ValueError as e:
        return ShareResult(
            success=False,
            message=str(e),
        )

    if not email or not isinstance(email, str):
        return ShareResult(
            success=False,
            message="email must be a non-empty string",
        )

    email = email.strip().lower()

    try:
        service = get_drive_service()

        # First, find the permission ID for this email
        permissions = service.permissions().list(
            fileId=file_id,
            supportsAllDrives=True,
            fields="permissions(id, emailAddress)",
        ).execute()

        permission_id = None
        for perm in permissions.get("permissions", []):
            if perm.get("emailAddress", "").lower() == email:
                permission_id = perm.get("id")
                break

        if not permission_id:
            return ShareResult(
                success=False,
                message=f"No permission found for {email}",
            )

        # Remove the permission
        service.permissions().delete(
            fileId=file_id,
            permissionId=permission_id,
            supportsAllDrives=True,
        ).execute()

        return ShareResult(
            success=True,
            message=f"Removed permission for {email}",
        )

    except GoogleAuthError as e:
        logger.error(f"Remove sharing failed: {e}")
        return ShareResult(
            success=False,
            message=str(e),
        )
    except Exception as e:
        logger.error(f"Remove sharing failed: {e}")
        return ShareResult(
            success=False,
            message=str(e),
        )
