"""Factory for creating fastmcp.Client instances from ServerConfig."""

from __future__ import annotations

import logging
import os
from typing import Optional

from fastmcp import Client
from fastmcp.client.transports import (
    StdioTransport,
    SSETransport,
    StreamableHttpTransport,
)

from .config import ServerConfig
from .exceptions import ConnectionError

logger = logging.getLogger(__name__)


def create_client(config: ServerConfig, timeout: Optional[float] = 30.0) -> Client:
    """Create a fastmcp.Client based on the server configuration.

    Args:
        config: Server configuration.
        timeout: Connection timeout in seconds.

    Returns:
        Configured fastmcp.Client instance.

    Raises:
        ConnectionError: If the transport type is unknown or config is invalid.
    """
    try:
        if config.transport == "stdio":
            return _create_stdio_client(config, timeout)
        elif config.transport == "sse":
            return _create_sse_client(config, timeout)
        elif config.transport == "http":
            return _create_http_client(config, timeout)
        else:
            raise ConnectionError(f"Unknown transport type: {config.transport}")
    except ConnectionError:
        raise
    except Exception as e:
        raise ConnectionError(f"Failed to create client: {e}") from e


def _create_stdio_client(config: ServerConfig, timeout: Optional[float]) -> Client:
    """Create a client using stdio transport (subprocess)."""
    command = config.command
    if not command:
        raise ConnectionError("stdio transport requires 'command' in config")

    # Merge environment variables
    env = {**os.environ, **config.env}

    transport = StdioTransport(
        command=command,
        args=config.args,
        env=env,
    )
    return Client(transport=transport, timeout=timeout)


def _create_sse_client(config: ServerConfig, timeout: Optional[float]) -> Client:
    """Create a client using SSE transport."""
    url = config.url
    if not url:
        raise ConnectionError("sse transport requires 'url' in config")

    transport = SSETransport(
        url=url,
        headers=config.headers or None,
    )
    return Client(transport=transport, timeout=timeout)


def _create_http_client(config: ServerConfig, timeout: Optional[float]) -> Client:
    """Create a client using HTTP streamable transport."""
    url = config.url
    if not url:
        raise ConnectionError("http transport requires 'url' in config")

    transport = StreamableHttpTransport(
        url=url,
        headers=config.headers or None,
    )
    return Client(transport=transport, timeout=timeout)
