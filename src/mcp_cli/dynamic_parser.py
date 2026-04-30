"""Dynamic subcommand builder based on MCP tool discovery."""

from __future__ import annotations

import argparse
from typing import Any, Dict, List, Optional

from . import schema_to_argparse
from .output import format_tool_list


def build_dynamic_parser(
    tools: list,
    program: str = "mcp-cli",
    server_name: str = "",
) -> argparse.ArgumentParser:
    """Build an ArgumentParser with subcommands for each MCP tool.

    Also adds built-in 'list' and 'guide' commands.

    Args:
        tools: List of Tool objects from list_tools().
        program: Program name for help display.
        server_name: Server name for help display context.

    Returns:
        Configured ArgumentParser with tool subcommands.
    """
    parser = argparse.ArgumentParser(
        prog=program,
        description=f"MCP-CLI: interact with '{server_name}' MCP server tools.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output results in JSON format",
    )

    subparsers = parser.add_subparsers(
        dest="tool_command",
        help="Available tool commands",
    )

    # Built-in 'list' command
    list_parser = subparsers.add_parser(
        "list",
        help="List all available tools",
    )

    # Built-in 'guide' command
    guide_parser = subparsers.add_parser(
        "guide",
        help="Generate Markdown usage guide",
    )
    guide_parser.add_argument(
        "--guide-dir",
        default="./mcp-docs",
        help="Output directory for generated guides (default: ./mcp-docs)",
    )

    # Add tool subcommands
    for tool in tools:
        tool_parser = subparsers.add_parser(
            tool.name,
            help=getattr(tool, "description", "") or f"Call {tool.name}",
            description=getattr(tool, "description", ""),
        )
        schema = getattr(tool, "inputSchema", {}) or {}
        if schema:
            schema_to_argparse.convert(tool_parser, schema)

    return parser


def parse_tool_args(
    parser: argparse.ArgumentParser,
    argv: List[str],
) -> argparse.Namespace:
    """Parse command-line arguments using the dynamic parser.

    Args:
        parser: The dynamic parser built by build_dynamic_parser.
        argv: Remaining command-line arguments after top-level parsing.

    Returns:
        Parsed namespace with tool_command and tool arguments.
    """
    return parser.parse_args(argv)


def collect_tool_arguments(
    namespace: argparse.Namespace,
    schema: Dict[str, Any],
) -> Dict[str, Any]:
    """Collect tool arguments from parsed namespace into a dict for call_tool.

    Args:
        namespace: Parsed argparse namespace.
        schema: JSON Schema of the tool's input.

    Returns:
        Dictionary of arguments for call_tool.
    """
    return schema_to_argparse.collect_args(namespace, schema)
