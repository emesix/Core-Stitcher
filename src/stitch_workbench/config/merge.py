from __future__ import annotations

from typing import Any


def merge_two(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Merge override into base. Override wins.

    Rules:
    - Scalars: override replaces base
    - Dicts: recursive deep merge
    - Lists: override replaces (no append)
    - null (None): removes key from base
    """
    result = dict(base)
    for key, value in override.items():
        if value is None:
            result.pop(key, None)
        elif isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge_two(result[key], value)
        else:
            result[key] = value
    return result


def _trace_keys(
    data: dict[str, Any],
    layer_name: str,
    prefix: str = "",
) -> dict[str, str]:
    """Build a flat map of dotted key paths to layer names."""
    result: dict[str, str] = {}
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            result.update(_trace_keys(value, layer_name, full_key))
        else:
            result[full_key] = layer_name
    return result


def merge_layers(
    managed: dict[str, Any],
    bootstrap: dict[str, Any],
    project: dict[str, Any],
    local: dict[str, Any],
    runtime: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, str]]:
    """Merge 5 settings layers into effective config.

    Precedence: managed > bootstrap > project > local > runtime.
    Higher priority layers are applied LAST so they win.

    Returns:
        (effective_config, value_sources) where value_sources maps
        dotted key paths to the layer name that provided the value.
    """
    # Apply from lowest priority to highest — highest applied last wins.
    layers_ordered = [
        ("runtime", runtime),
        ("local", local),
        ("project", project),
        ("bootstrap", bootstrap),
        ("managed", managed),
    ]

    effective: dict[str, Any] = {}
    sources: dict[str, str] = {}

    for layer_name, layer_data in layers_ordered:
        effective = merge_two(effective, layer_data)
        # Track which layer set each key
        sources.update(_trace_keys(layer_data, layer_name))
        # Remove source entries for keys that were null-removed
        for key in list(sources.keys()):
            parts = key.split(".")
            obj = effective
            found = True
            for part in parts[:-1]:
                if isinstance(obj, dict) and part in obj:
                    obj = obj[part]
                else:
                    found = False
                    break
            if found and isinstance(obj, dict) and parts[-1] not in obj:
                sources.pop(key, None)

    return effective, sources
