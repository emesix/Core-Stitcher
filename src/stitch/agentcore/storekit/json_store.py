"""JSON file store — one file per run in a directory."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from stitch.agentcore.storekit.models import RunRecord

if TYPE_CHECKING:
    from uuid import UUID


class JsonRunStore:
    """Persists RunRecords as individual JSON files in a directory."""

    def __init__(self, directory: str | Path) -> None:
        self._dir = Path(directory)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, run_id: UUID) -> Path:
        return self._dir / f"{run_id}.json"

    def save(self, run: RunRecord) -> None:
        data = run.model_dump(mode="json")
        self._path(run.run_id).write_text(json.dumps(data, indent=2))

    def get(self, run_id: UUID) -> RunRecord | None:
        path = self._path(run_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return RunRecord.model_validate(data)

    def list_runs(self) -> list[RunRecord]:
        runs = []
        for path in sorted(self._dir.glob("*.json")):
            try:
                data = json.loads(path.read_text())
                runs.append(RunRecord.model_validate(data))
            except (json.JSONDecodeError, ValueError):
                continue
        return runs

    def delete(self, run_id: UUID) -> bool:
        path = self._path(run_id)
        if path.exists():
            path.unlink()
            return True
        return False
