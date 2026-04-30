"""Main entry point for mcp-cli."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import List, Optional

from . import __version__
from .client_factory import create_client
from .config import load_config, MCPConfig
from .dynamic_parser import (
    build_dynamic_parser,
    collect_tool_arguments,
    parse_tool_args,
)
from .exceptions import (
    ConfigError,
    ConnectionError,
    MCPCliError,
    ServerNotFoundError,
    ToolCallError,
)
from .guide_generator import generate_guide, write_guide
from .output import format_result, format_tool_list, print_error, print_output


def _build_top_level_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="mcp-cli",
        description="MCP-CLI: A universal CLI proxy for MCP services.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--config", "-c",
        default=None,
        help="Path to MCP configuration file (default: mcp.json)",
    )
    parser.add_argument(
        "--server", "-s",
        default=None,
        help="MCP server name from config file",
    )
    parser.add_argument(
        "--timeout", "-t",
        type=float,
        default=30.0,
        help="Connection timeout in seconds (default: 30)",
    )
    return parser


def _preparse_args(argv: List[str]) -> tuple:
    """Pre-parse top-level arguments, return (known_args, remaining_argv)."""
    parser = _build_top_level_parser()
    return parser.parse_known_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    """Main entry point."""
    if argv is None:
        argv = sys.argv[1:]

    try:
        asyncio.run(_async_main(argv))
    except MCPCliError as e:
        print_error(str(e))
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)


async def _async_main(argv: List[str]) -> None:
    """Async main logic."""
    # Step 1: Pre-parse top-level arguments
    top_args, remaining = _preparse_args(argv)

    # Step 2: Load configuration
    config = load_config(top_args.config)

    # Step 3: If no --server, list available servers and exit
    if not top_args.server:
        _list_servers(config)
        return

    # Step 4: Get server config
    server_config = config.get_server(top_args.server)

    # Step 5: Create client, connect, and execute
    client = create_client(server_config, timeout=top_args.timeout)

    async with client:
        # Step 6: Discover tools
        tools = await client.list_tools()

        # Step 7: Build dynamic parser with tool subcommands
        dyn_parser = build_dynamic_parser(
            tools=tools,
            program=f"mcp-cli --server {top_args.server}",
            server_name=top_args.server,
        )

        # Step 8: If no subcommand provided, show help
        if not remaining:
            dyn_parser.print_help()
            return

        # Step 9: Parse tool-specific arguments
        args = parse_tool_args(dyn_parser, remaining)
        tool_command = args.tool_command

        if not tool_command:
            dyn_parser.print_help()
            return

        # Step 10: Execute the command
        if tool_command == "list":
            _handle_list(tools, json_output=args.json)
        elif tool_command == "guide":
            await _handle_guide(
                client=client,
                config=config,
                server_name=top_args.server,
                tools=tools,
                guide_dir=args.guide_dir,
            )
        else:
            await _handle_tool_call(
                client=client,
                tools=tools,
                tool_name=tool_command,
                args=args,
                json_output=args.json,
            )


def _list_servers(config: MCPConfig) -> None:
    """List all configured servers."""
    lines = [
        "Available MCP servers:",
        "",
    ]
    for name in config.server_names:
        server_cfg = config.mcpServers[name]
        lines.append(f"  {name:<20s} {server_cfg.display_info}")
    lines.append("")
    lines.append("Use --server <name> to select a server.")
    lines.append("Example: mcp-cli --server <name> list")
    print_output("\n".join(lines))


def _handle_list(tools: list, json_output: bool = False) -> None:
    """Handle the 'list' built-in command."""
    if json_output:
        tool_info = []
        for tool in tools:
            tool_info.append({
                "name": tool.name,
                "description": getattr(tool, "description", ""),
            })
        print_output(json.dumps(tool_info, indent=2, ensure_ascii=False))
    else:
        print_output(format_tool_list(tools))


async def _handle_guide(
    client,
    config: MCPConfig,
    server_name: str,
    tools: list,
    guide_dir: str,
) -> None:
    """Handle the 'guide' built-in command."""
    # Generate guide for current server
    content = generate_guide(server_name, tools)
    path = write_guide(server_name, content, guide_dir)
    print_output(f"Guide generated: {path}")


async def _handle_tool_call(
    client,
    tools: list,
    tool_name: str,
    args: argparse.Namespace,
    json_output: bool,
) -> None:
    """Handle a tool invocation command."""
    # Find the tool schema
    tool = None
    for t in tools:
        if t.name == tool_name:
            tool = t
            break

    if tool is None:
        raise ToolCallError(f"Tool '{tool_name}' not found on server.")

    schema = getattr(tool, "inputSchema", {}) or {}
    arguments = collect_tool_arguments(args, schema)

    # Call the tool
    try:
        result = await client.call_tool(tool_name, arguments)
    except Exception as e:
        raise ToolCallError(f"Tool call failed: {e}") from e

    # Check if result indicates an error
    if hasattr(result, "is_error") and result.is_error:
        error_text = format_result(result, json_output=True)
        print_error(f"Tool returned an error:", error_text)
        sys.exit(1)

    # Format and output
    formatted = format_result(result, json_output=json_output)
    print_output(formatted)


if __name__ == "__main__":
    main()
