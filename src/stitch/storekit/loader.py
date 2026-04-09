from __future__ import annotations

import json
from pathlib import Path

from stitch.modelkit.topology import TopologySnapshot

SUPPORTED_VERSIONS = {"1.0"}


class TopologyVersionError(Exception):
    def __init__(self, version: str) -> None:
        self.version = version
        super().__init__(
            f"Unsupported topology schema version '{version}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_VERSIONS))}"
        )


def load_topology(path: str | Path) -> TopologySnapshot:
    path = Path(path)
    raw = json.loads(path.read_text(encoding="utf-8"))

    version = raw.get("meta", {}).get("version")
    if version not in SUPPORTED_VERSIONS:
        raise TopologyVersionError(version or "missing")

    return TopologySnapshot.model_validate(raw)


def save_topology(snapshot: TopologySnapshot, path: str | Path) -> None:
    path = Path(path)
    data = snapshot.model_dump(mode="json")
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
