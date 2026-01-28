"""
Arcade client management with singleton pattern and authorization caching.
"""

import logging
from typing import Any, Optional

from arcadepy import Arcade

from .config import get_config

logger = logging.getLogger(__name__)

# Singleton client instance
_client: Optional[Arcade] = None

# Cache of tools that have been authorized for the current session
_authorized_tools: set[str] = set()


class ArcadeAuthError(Exception):
    """Raised when Arcade authorization fails."""

    pass


class ArcadeToolError(Exception):
    """Raised when a tool execution fails."""

    pass


def get_arcade_client() -> Arcade:
    """Get the singleton Arcade client instance.

    Creates a new client on first call, reuses it on subsequent calls.
    This avoids creating multiple client instances which is inefficient.

    Returns:
        Arcade: The Arcade client instance.

    Raises:
        ValueError: If API key is not configured.
    """
    global _client
    if _client is None:
        config = get_config()
        _client = Arcade(api_key=config.arcade_api_key)
        logger.debug("Created new Arcade client instance")
    return _client


def reset_client() -> None:
    """Reset the singleton client and authorization cache.

    Useful for testing or when credentials change.
    """
    global _client, _authorized_tools
    _client = None
    _authorized_tools.clear()
    logger.debug("Reset Arcade client and authorization cache")


def authorize_tool(tool_name: str) -> None:
    """Authorize a tool if not already authorized.

    Uses a cache to avoid redundant authorization API calls.

    Args:
        tool_name: The name of the tool to authorize (e.g., "Google.ListFiles").

    Raises:
        ArcadeAuthError: If authorization fails.
    """
    global _authorized_tools

    if tool_name in _authorized_tools:
        logger.debug(f"Tool {tool_name} already authorized (cached)")
        return

    client = get_arcade_client()
    config = get_config()

    try:
        auth_response = client.tools.authorize(
            tool_name=tool_name,
            user_id=config.arcade_user_id,
        )

        if auth_response.status != "completed":
            # Check for authorization URL in various attributes
            auth_url = getattr(auth_response, "authorization_url", None) or getattr(auth_response, "url", None)
            if auth_url:
                print(f"\n🔐 Authorization required for {tool_name}")
                print(f"   Please visit: {auth_url}")
                print("   Waiting for authorization...\n")
                # Wait for authorization to complete
                client.auth.wait_for_completion(auth_response)
                _authorized_tools.add(tool_name)
                print(f"   ✓ Authorization complete for {tool_name}!\n")
                return
            raise ArcadeAuthError(
                f"Authorization failed for {tool_name}. Status: {auth_response.status}"
            )

        _authorized_tools.add(tool_name)
        logger.debug(f"Successfully authorized tool: {tool_name}")

    except ArcadeAuthError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error authorizing {tool_name}: {e}")
        raise ArcadeAuthError(f"Failed to authorize {tool_name}: {e}") from e


def execute_tool(tool_name: str, **kwargs: Any) -> dict[str, Any]:
    """Execute an Arcade tool with automatic authorization.

    Authorizes the tool if needed (using cache), then executes it.

    Args:
        tool_name: The name of the tool to execute.
        **kwargs: Arguments to pass to the tool.

    Returns:
        dict: The tool execution result.

    Raises:
        ArcadeAuthError: If authorization fails.
        ArcadeToolError: If tool execution fails.
    """
    # Ensure tool is authorized (uses cache)
    authorize_tool(tool_name)

    client = get_arcade_client()
    config = get_config()

    try:
        response = client.tools.execute(
            tool_name=tool_name,
            user_id=config.arcade_user_id,
            input=kwargs,
        )

        if not response.output:
            raise ArcadeToolError(f"Tool {tool_name} returned no output")

        result = response.output.value
        if result is None:
            raise ArcadeToolError(f"Tool {tool_name} returned None value")

        return result

    except (ArcadeAuthError, ArcadeToolError):
        raise
    except Exception as e:
        logger.error(f"Unexpected error executing {tool_name}: {e}")
        raise ArcadeToolError(f"Failed to execute {tool_name}: {e}") from e


def get_authorized_tools() -> set[str]:
    """Get the set of currently authorized tools.

    Returns:
        set[str]: Set of tool names that have been authorized.
    """
    return _authorized_tools.copy()


def is_tool_authorized(tool_name: str) -> bool:
    """Check if a tool has been authorized.

    Args:
        tool_name: The name of the tool to check.

    Returns:
        bool: True if the tool is in the authorization cache.
    """
    return tool_name in _authorized_tools
