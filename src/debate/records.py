"""Exclusive run artifacts; preserve adapter text exactly as UTF-8 bytes."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import uuid


class RecordStoreError(ValueError):
    pass


class RecordStore:
    def __init__(self, record_root: str | Path):
        if not str(record_root):
            raise RecordStoreError("record_root_required")
        self.root = Path(record_root).resolve()
        if self.root.exists() and not self.root.is_dir():
            raise RecordStoreError("record_root_not_directory")
        self.root.mkdir(parents=True, exist_ok=True)

    def _contained(self, path: Path) -> Path:
        path = Path(path).resolve()
        if path == self.root or not path.is_relative_to(self.root):
            raise RecordStoreError("artifact_outside_record_root")
        return path

    def create_run(self, run_id: str | None = None) -> Path:
        name = run_id if run_id is not None else "run_" + uuid.uuid4().hex
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_]{1,128}", name):
            raise RecordStoreError("invalid_run_id")
        path = self._contained(self.root / name)
        path.mkdir()
        (path / "raw").mkdir()
        return path

    def write_json_once(self, path: Path, value: object) -> None:
        # Serialize before opening so invalid data cannot leave a partial JSON record.
        data = json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, indent=2) + "\n"
        self.write_raw_once(path, data)

    def write_raw_once(self, path: Path, content: str) -> dict:
        path = self._contained(path)
        data = content.encode("utf-8")
        with path.open("xb") as handle:
            handle.write(data)
        return {"path": str(path), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}

    @staticmethod
    def timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()
