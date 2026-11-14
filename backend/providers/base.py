from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class DataProvider(ABC):
    """Contrato para proveedores temporales. Cada implementación devuelve metadatos y observaciones verificables."""

    provider_id: str

    @abstractmethod
    def fetch_monthly(
        self, *, parameter: str, latitude: float, longitude: float, start_year: int, end_year: int,
    ) -> dict[str, Any]:
        raise NotImplementedError
