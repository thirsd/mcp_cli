"""Custom exceptions for mcp-cli."""


class MCPCliError(Exception):
    """Base exception for mcp-cli."""


class ConfigError(MCPCliError):
    """Configuration file related error."""


class ServerNotFoundError(MCPCliError):
    """Requested server name not found in configuration."""


class ConnectionError(MCPCliError):
    """Failed to connect to MCP server."""


class ToolCallError(MCPCliError):
    """Error during tool invocation."""


class SchemaConversionError(MCPCliError):
    """Error converting JSON Schema to argparse arguments."""
