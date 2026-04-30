"""Convert JSON Schema to argparse arguments."""

from __future__ import annotations

import argparse
import json
import re
from typing import Any, Dict, List, Optional, Tuple


def _camel_to_kebab(name: str) -> str:
    """Convert camelCase to kebab-case for CLI argument names."""
    # Insert hyphen before uppercase letters, then lowercase everything
    s1 = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1-\2", name)
    return re.sub(r"([a-z\d])([A-Z])", r"\1-\2", s1).lower()


def _snake_to_kebab(name: str) -> str:
    """Convert snake_case to kebab-case."""
    return name.replace("_", "-")


def convert(
    parser: argparse.ArgumentParser,
    schema: Dict[str, Any],
    prefix: str = "",
) -> List[str]:
    """Add argparse arguments from a JSON Schema object.

    Args:
        parser: The argparse parser to add arguments to.
        schema: JSON Schema dict (the top-level object schema).
        prefix: Prefix for nested property flattening (e.g., "address-").

    Returns:
        List of property names (original keys from schema) that were registered.
    """
    if not schema or schema.get("type") != "object":
        return []

    properties = schema.get("properties", {})
    required_fields = set(schema.get("required", []))
    registered: List[str] = []

    for prop_name, prop_schema in properties.items():
        cli_name = _camel_to_kebab(prop_name)
        full_cli_name = f"--{prefix}{cli_name}" if prefix else f"--{cli_name}"
        is_required = prop_name in required_fields

        _add_argument(
            parser=parser,
            cli_name=full_cli_name,
            dest=prop_name,
            prop_schema=prop_schema,
            is_required=is_required,
            prefix=prefix,
        )
        registered.append(prop_name)

    return registered


def _add_argument(
    parser: argparse.ArgumentParser,
    cli_name: str,
    dest: str,
    prop_schema: Dict[str, Any],
    is_required: bool,
    prefix: str,
) -> None:
    """Add a single argparse argument based on a JSON Schema property."""
    prop_type = prop_schema.get("type", "string")
    description = prop_schema.get("description", "")
    default = prop_schema.get("default")
    enum_values = prop_schema.get("enum")

    # Handle enum regardless of type
    if enum_values:
        kwargs: Dict[str, Any] = {
            "dest": dest,
            "help": description,
            "choices": enum_values,
            "type": str,
        }
        if default is not None:
            kwargs["default"] = default
        if is_required and default is None:
            kwargs["required"] = True
        parser.add_argument(cli_name, **kwargs)
        return

    # Handle object type: try flattening one level, else JSON passthrough
    if prop_type == "object":
        nested_props = prop_schema.get("properties", {})
        if nested_props and not prefix:  # Only flatten one level
            _flatten_object(parser, dest, prop_schema, is_required)
            return
        # Fall through to JSON passthrough
        _add_json_argument(parser, cli_name, dest, description, is_required, default)
        return

    # Handle array type
    if prop_type == "array":
        items = prop_schema.get("items", {})
        item_type = items.get("type", "string")

        # Simple type arrays: use nargs='*'
        if item_type in ("string", "integer", "number"):
            type_map = {"string": str, "integer": int, "number": float}
            kwargs = {
                "dest": dest,
                "help": description,
                "nargs": "*",
                "type": type_map[item_type],
            }
            if default is not None:
                kwargs["default"] = default
            parser.add_argument(cli_name, **kwargs)
            return

        # Complex arrays: JSON passthrough
        _add_json_argument(parser, cli_name, dest, description, is_required, default)
        return

    # Handle anyOf/oneOf: fall back to JSON passthrough
    if "anyOf" in prop_schema or "oneOf" in prop_schema:
        _add_json_argument(parser, cli_name, dest, description, is_required, default)
        return

    # Handle boolean
    if prop_type == "boolean":
        if default is True:
            parser.add_argument(
                cli_name,
                dest=dest,
                help=description,
                action="store_false",
                default=True,
            )
        else:
            parser.add_argument(
                cli_name,
                dest=dest,
                help=description,
                action="store_true",
                default=False,
            )
        return

    # Handle string, integer, number
    type_map = {"string": str, "integer": int, "number": float}
    arg_type = type_map.get(prop_type, str)

    kwargs = {
        "dest": dest,
        "help": description,
        "type": arg_type,
    }
    if default is not None:
        kwargs["default"] = default
    if is_required and default is None:
        kwargs["required"] = True

    parser.add_argument(cli_name, **kwargs)


def _add_json_argument(
    parser: argparse.ArgumentParser,
    cli_name: str,
    dest: str,
    description: str,
    is_required: bool,
    default: Any,
) -> None:
    """Add an argument that accepts a JSON string."""
    kwargs: Dict[str, Any] = {
        "dest": dest,
        "help": f"{description} (JSON string)" if description else "JSON string",
        "type": _json_loads,
    }
    if default is not None:
        kwargs["default"] = default
    if is_required and default is None:
        kwargs["required"] = True
    parser.add_argument(cli_name, **kwargs)


def _flatten_object(
    parser: argparse.ArgumentParser,
    parent_name: str,
    prop_schema: Dict[str, Any],
    parent_required: bool,
) -> None:
    """Flatten an object property into prefixed CLI arguments.

    E.g., object 'address' with 'city' and 'street' becomes
    --address-city and --address-street.
    """
    nested_props = prop_schema.get("properties", {})
    nested_required = set(prop_schema.get("required", []))

    for sub_name, sub_schema in nested_props.items():
        sub_cli = _camel_to_kebab(sub_name)
        full_cli = f"--{_camel_to_kebab(parent_name)}-{sub_cli}"
        is_required = parent_required and sub_name in nested_required
        _add_argument(
            parser=parser,
            cli_name=full_cli,
            dest=f"{parent_name}.{sub_name}",
            prop_schema=sub_schema,
            is_required=is_required,
            prefix=f"{_camel_to_kebab(parent_name)}-",
        )


def _json_loads(value: str) -> Any:
    """Parse a JSON string, raising argparse error on failure."""
    try:
        return json.loads(value)
    except json.JSONDecodeError as e:
        raise argparse.ArgumentTypeError(f"Invalid JSON: {e}")


def collect_args(
    namespace: argparse.Namespace,
    schema: Dict[str, Any],
    prefix: str = "",
) -> Dict[str, Any]:
    """Collect parsed arguments into a dict matching the original schema structure.

    Handles:
    - Simple types: direct mapping
    - Flattened objects: re-nest dotted keys
    - JSON passthrough: already parsed
    - Simple arrays: already collected as lists

    Args:
        namespace: Parsed argparse namespace.
        schema: Original JSON Schema.

    Returns:
        Dictionary ready for call_tool arguments.
    """
    if not schema or schema.get("type") != "object":
        return {}

    properties = schema.get("properties", {})
    required_fields = set(schema.get("required", []))
    result: Dict[str, Any] = {}

    for prop_name, prop_schema in properties.items():
        prop_type = prop_schema.get("type", "string")
        enum_values = prop_schema.get("enum")
        default = prop_schema.get("default")

        # Object with flattening: collect nested keys
        if prop_type == "object" and prop_schema.get("properties") and not prefix:
            nested = _collect_flattened(namespace, prop_name, prop_schema)
            if nested is not None:
                result[prop_name] = nested
            continue

        # Get value from namespace
        value = getattr(namespace, prop_name, None)

        # Skip if not provided and not required
        if value is None and prop_name not in required_fields and default is None:
            continue

        if value is not None:
            result[prop_name] = value
        elif default is not None:
            result[prop_name] = default

    return result


def _collect_flattened(
    namespace: argparse.Namespace,
    parent_name: str,
    prop_schema: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Collect flattened object properties back into a nested dict."""
    nested_props = prop_schema.get("properties", {})
    result: Dict[str, Any] = {}
    has_value = False

    for sub_name in nested_props:
        dotted_key = f"{parent_name}.{sub_name}"
        value = getattr(namespace, dotted_key, None)
        if value is not None:
            result[sub_name] = value
            has_value = True

    return result if has_value else None
