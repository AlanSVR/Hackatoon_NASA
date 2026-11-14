from __future__ import annotations

import json
from datetime import UTC, datetime
from threading import Lock
from uuid import uuid4


class ExportStore:
    """Exportaciones efímeras ligadas a la sesión local del proceso."""

    def __init__(self, max_entries: int = 32):
        self.max_entries = max_entries
        self._items: dict[str, dict] = {}
        self._lock = Lock()

    def put(self, report: dict) -> str:
        export_id = uuid4().hex
        with self._lock:
            self._items[export_id] = {
                'created_at': datetime.now(UTC).isoformat(),
                'report': report,
            }
            if len(self._items) > self.max_entries:
                oldest = next(iter(self._items))
                self._items.pop(oldest, None)
        return export_id

    def get(self, export_id: str) -> dict | None:
        with self._lock:
            item = self._items.get(export_id)
            return dict(item) if item else None

    @staticmethod
    def as_json(report: dict) -> str:
        return json.dumps(report, ensure_ascii=False, indent=2)

    @staticmethod
    def as_csv(report: dict) -> str:
        rows = ['date,value']
        for item in report.get('series', {}).get('observations', []):
            value = '' if item.get('value') is None else item['value']
            rows.append(f"{item.get('date', '')},{value}")
        return '\n'.join(rows) + '\n'
