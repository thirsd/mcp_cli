"""Configuration file reading and model definitions."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

from .exceptions import ConfigError, ServerNotFoundError


class ServerConfig(BaseModel):
    """Configuration for a single MCP server."""

    transport: Literal["stdio", "sse", "http"] = "stdio"
    command: Optional[str] = None
    args: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)
    url: Optional[str] = None
    headers: Dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_transport_fields(self) -> "ServerConfig":
        if self.transport == "stdio":
            if not self.command:
                raise ValueError(
                    "stdio transport requires 'command' field"
                )
        elif self.transport in ("sse", "http"):
            if not self.url:
                raise ValueError(
                    f"{self.transport} transport requires 'url' field"
                )
        return self

    @property
    def display_info(self) -> str:
        """Return a short description for display purposes."""
        if self.transport == "stdio":
            cmd = self.command or ""
            arg_str = " ".join(self.args[:2])
            return f"[stdio] {cmd} {arg_str}".strip()
        return f"[{self.transport}] {self.url}"


class MCPConfig(BaseModel):
    """Top-level configuration model matching Claude Code format."""

    mcpServers: Dict[str, ServerConfig]

    def get_server(self, name: str) -> ServerConfig:
        """Get server config by name, raise if not found."""
        if name not in self.mcpServers:
            available = ", ".join(sorted(self.mcpServers.keys()))
            raise ServerNotFoundError(
                f"Server '{name}' not found. Available servers: {available}"
            )
        return self.mcpServers[name]

    @property
    def server_names(self) -> List[str]:
        return sorted(self.mcpServers.keys())


# Default search paths for config file
_DEFAULT_CONFIG_PATHS = [
    "mcp.json",
    "mcp_config.json",
]


def load_config(config_path: Optional[str] = None) -> MCPConfig:
    """Load and validate MCP configuration from a JSON file.

    Args:
        config_path: Explicit path to config file. If None, searches
                     default locations and MCP_CLI_CONFIG env var.

    Returns:
        Validated MCPConfig instance.

    Raises:
        ConfigError: If config file cannot be found or parsed.
    """
    # Determine config file path
    path = _resolve_config_path(config_path)

    if not path.exists():
        raise ConfigError(f"Configuration file not found: {path}")

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid JSON in config file: {e}") from e

    if "mcpServers" not in raw:
        raise ConfigError(
            "Config file must contain 'mcpServers' field. "
            "See Claude Code MCP configuration format for reference."
        )

    try:
        return MCPConfig.model_validate(raw)
    except Exception as e:
        raise ConfigError(f"Invalid configuration: {e}") from e


def _resolve_config_path(config_path: Optional[str]) -> Path:
    """Resolve the configuration file path."""
    # 1. Explicit path
    if config_path:
        return Path(config_path)

    # 2. Environment variable
    env_path = os.environ.get("MCP_CLI_CONFIG")
    if env_path:
        return Path(env_path)

    # 3. Default search paths
    for name in _DEFAULT_CONFIG_PATHS:
        candidate = Path(name)
        if candidate.exists():
            return candidate

    # Return default (will fail in load_config with clear message)
    return Path("mcp.json")
