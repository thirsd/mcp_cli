"""Markdown guide generator for MCP service tools."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional


def generate_guide(
    server_name: str,
    tools: list,
) -> str:
    """Generate a Markdown guide for a server's tools.

    Args:
        server_name: Name of the MCP server.
        tools: List of Tool objects from list_tools().

    Returns:
        Complete Markdown string.
    """
    lines: List[str] = []
    lines.append(f"# {server_name} MCP 服务命令指南")
    lines.append("")
    lines.append(f"> 自动生成自 `{server_name}` MCP 服务端工具列表。")
    lines.append("")

    # Summary table
    lines.append("## 工具概览")
    lines.append("")
    lines.append("| 工具名 | 描述 |")
    lines.append("|--------|------|")
    for tool in tools:
        desc = getattr(tool, "description", "") or "No description"
        short_desc = desc.split("\n")[0][:60]
        lines.append(f"| `{tool.name}` | {short_desc} |")
    lines.append("")

    # Detailed tool sections
    lines.append("## 工具详情")
    lines.append("")

    for tool in tools:
        lines.extend(_generate_tool_section(server_name, tool))
        lines.append("")

    return "\n".join(lines)


def _generate_tool_section(server_name: str, tool: Any) -> List[str]:
    """Generate the Markdown section for a single tool."""
    lines: List[str] = []
    desc = getattr(tool, "description", "") or "No description"
    schema = getattr(tool, "inputSchema", {}) or {}

    lines.append(f"### `{tool.name}`")
    lines.append("")
    lines.append(f"**描述**：{desc}")
    lines.append("")

    # Parameter table
    properties = schema.get("properties", {})
    required_fields = set(schema.get("required", []))

    if properties:
        lines.append("**参数**：")
        lines.append("")
        lines.append("| 参数名 | 类型 | 必填 | 默认值 | 说明 |")
        lines.append("|--------|------|------|--------|------|")

        for prop_name, prop_schema in properties.items():
            prop_type = prop_schema.get("type", "string")
            is_required = "是" if prop_name in required_fields else "否"
            default = prop_schema.get("default", "-")
            if default != "-":
                default = f"`{default}`"
            prop_desc = prop_schema.get("description", "")
            enum_values = prop_schema.get("enum")
            if enum_values:
                prop_desc += f" 可选值: {', '.join(f'`{v}`' for v in enum_values)}"
            lines.append(
                f"| `--{prop_name}` | `{prop_type}` | {is_required} | {default} | {prop_desc} |"
            )
        lines.append("")
    else:
        lines.append("此工具无需参数。")
        lines.append("")

    # Usage example
    lines.append("**使用示例**：")
    lines.append("```bash")
    example_args = _build_example_args(schema)
    lines.append(
        f"mcp-cli --server {server_name} {tool.name} {example_args}"
    )
    lines.append("```")

    return lines


def _build_example_args(schema: Dict[str, Any]) -> str:
    """Build example CLI arguments from a JSON Schema."""
    properties = schema.get("properties", {})
    if not properties:
        return ""

    parts: List[str] = []
    for prop_name, prop_schema in properties.items():
        prop_type = prop_schema.get("type", "string")
        enum_values = prop_schema.get("enum")

        if enum_values:
            parts.append(f"--{prop_name} {enum_values[0]}")
        elif prop_type == "boolean":
            parts.append(f"--{prop_name}")
        elif prop_type == "integer":
            parts.append(f"--{prop_name} 42")
        elif prop_type == "number":
            parts.append(f"--{prop_name} 3.14")
        elif prop_type == "array":
            parts.append(f'--{prop_name} item1 item2')
        elif prop_type == "object":
            parts.append(f'--{prop_name} \'{{"key": "value"}}\'')
        else:
            parts.append(f"--{prop_name} <{prop_name}>")

    return " ".join(parts)


def write_guide(
    server_name: str,
    content: str,
    output_dir: str = "./mcp-docs",
) -> str:
    """Write the generated guide to a Markdown file.

    Args:
        server_name: Server name (used for filename).
        content: Markdown content string.
        output_dir: Output directory path.

    Returns:
        Path to the written file.
    """
    dir_path = Path(output_dir)
    dir_path.mkdir(parents=True, exist_ok=True)

    file_path = dir_path / f"{server_name}.md"
    file_path.write_text(content, encoding="utf-8")

    return str(file_path)
