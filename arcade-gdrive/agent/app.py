"""Streamlit chat app for Google Drive operations via Claude agent."""

from __future__ import annotations

import json
import os
import sys

import streamlit as st
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Load .env from project root
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from anthropic import Anthropic
from agent.tools import TOOL_DEFINITIONS, execute_tool

SYSTEM_PROMPT = """\
You are a Google Drive assistant for a professional services PM.
You manage project folders in Google Drive (My Drive and Shared Drives).

## Key Behaviors

1. **Search Strategy**: Google Drive search is recursive by default - it searches through ALL subfolders.
   - To find folders like "[20] Build" within a specific location:
     a) First find the parent folder ID (e.g., search for "_FULL DELIVERABLE" or the project folder)
     b) Then search within that folder using the parent_id parameter
   - Or simply search for "[20] Build" with file_type="folder" across all drives

2. **Finding nested folders**: If user says "find [X] within folder Y":
   - First: search for folder Y to get its ID
   - Then: search for X with parent_id set to Y's ID

3. **Shared Drives**: When user mentions a Shared Drive name (like "Product", "Operations"):
   - Use get_user_info to see available Shared Drives and their IDs
   - Folders within Shared Drives are searchable like any other folder

4. Always confirm destructive actions (delete, move) before executing.
5. Format folder/file URLs as clickable markdown links when available.
6. When showing search results, include the file ID so the user can reference it later.
"""


def get_anthropic_client() -> Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        st.error("Set the ANTHROPIC_API_KEY environment variable.")
        st.stop()
    return Anthropic(api_key=api_key)


def call_claude(client: Anthropic, messages: list[dict]) -> dict:
    """Send messages to Claude and return the response, handling tool use loops."""
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=TOOL_DEFINITIONS,
        messages=messages,
    )
    return response


def process_response(client: Anthropic, response, messages: list[dict]) -> str:
    """Process Claude's response, executing tool calls as needed.

    Returns the final text response.
    """
    # Collect all content blocks from this response
    assistant_content = list(response.content)

    while response.stop_reason == "tool_use":
        # Build tool results for every tool_use block in this response
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                tool_name = block.name
                tool_input = block.input

                # Show tool execution in an expander
                with st.expander(f"🔧 {tool_name}", expanded=False):
                    st.json(tool_input)
                    result = execute_tool(tool_name, tool_input)
                    st.json(result)

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                })

        # Append assistant turn and tool results, then call Claude again
        messages.append({"role": "assistant", "content": assistant_content})
        messages.append({"role": "user", "content": tool_results})

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )
        assistant_content = list(response.content)

    # Extract final text
    text_parts = [block.text for block in response.content if hasattr(block, "text")]
    final_text = "\n".join(text_parts)

    # Append final assistant message to history
    messages.append({"role": "assistant", "content": assistant_content})

    return final_text


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

st.set_page_config(page_title="GDrive PM Assistant", page_icon="📁")
st.title("📁 Google Drive PM Assistant")

# Session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "display_messages" not in st.session_state:
    st.session_state.display_messages = []

# Render chat history
for msg in st.session_state.display_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
if prompt := st.chat_input("Ask me to manage your Google Drive..."):
    # Show user message
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.display_messages.append({"role": "user", "content": prompt})

    # Add to Claude message history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Call Claude
    anthropic_client = get_anthropic_client()
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = call_claude(anthropic_client, st.session_state.messages)
            final_text = process_response(
                anthropic_client, response, st.session_state.messages
            )
        st.markdown(final_text)

    st.session_state.display_messages.append(
        {"role": "assistant", "content": final_text}
    )
