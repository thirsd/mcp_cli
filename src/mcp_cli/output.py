"""Output formatting module for JSON, text, and error display."""

from __future__ import annotations

import json
import sys
from typing import Any, List

from mcp.types import TextContent, ImageContent, EmbeddedResource


def format_result(result: Any, json_output: bool = False) -> str:
    """Format a tool call result for display.

    Args:
        result: The raw result from call_tool (CallToolResult or similar).
        json_output: If True, output raw JSON.

    Returns:
        Formatted string.
    """
    # Handle CallToolResult-like objects
    content = _extract_content(result)

    if json_output:
        return _to_json(content)

    return _to_text(content)


def _extract_content(result: Any) -> Any:
    """Extract content from various result types."""
    # CallToolResult has .content attribute
    if hasattr(result, "content"):
        items = result.content
        extracted = []
        for item in items:
            if isinstance(item, TextContent):
                extracted.append(item.text)
            elif isinstance(item, ImageContent):
                extracted.append(f"[Image: {item.mime_type}]")
            elif isinstance(item, EmbeddedResource):
                extracted.append(str(item))
            else:
                extracted.append(str(item))
        if len(extracted) == 1:
            # Try to parse as JSON for structured output
            try:
                return json.loads(extracted[0])
            except (json.JSONDecodeError, ValueError):
                return extracted[0]
        return extracted

    # Direct content list
    if isinstance(result, list):
        extracted = []
        for item in result:
            if isinstance(item, TextContent):
                extracted.append(item.text)
            elif isinstance(item, ImageContent):
                extracted.append(f"[Image: {item.mime_type}]")
            else:
                extracted.append(str(item))
        return extracted

    # Already a simple value
    return result


def _to_json(data: Any) -> str:
    """Format data as pretty-printed JSON."""
    return json.dumps(data, indent=2, ensure_ascii=False)


def _to_text(data: Any) -> str:
    """Format data as human-readable text."""
    if isinstance(data, str):
        return data
    if isinstance(data, (dict, list)):
        return _to_json(data)
    return str(data)


def format_tool_list(tools: list) -> str:
    """Format a list of tools for display.

    Args:
        tools: List of Tool objects.

    Returns:
        Formatted string.
    """
    if not tools:
        return "No tools available."

    lines = ["Available tools:", ""]
    for tool in tools:
        desc = getattr(tool, "description", "") or "No description"
        # Truncate long descriptions
        short_desc = desc.split("\n")[0][:80]
        lines.append(f"  {tool.name:<30s} {short_desc}")

    return "\n".join(lines)


def print_error(message: str, details: str = "") -> None:
    """Print error message to stderr.

    Args:
        message: Primary error message.
        details: Optional additional details.
    """
    print(f"Error: {message}", file=sys.stderr)
    if details:
        print(details, file=sys.stderr)


def print_output(text: str) -> None:
    """Print formatted output to stdout."""
    print(text)
