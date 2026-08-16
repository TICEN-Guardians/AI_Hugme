from dataclasses import dataclass
from typing import Any

from app.diagnosis.external.building_ledger.schemas import (
    BuildingLedgerKey,
)


@dataclass(frozen=True)
class ResolvedAddress:
    road_address: str
    jibun_address: str
    legal_dong_code: str
    district: str
    building_name: str | None
    available_dongs: tuple[str, ...]
    building_ledger_key: BuildingLedgerKey

@dataclass(frozen=True)
class AddressSearchResult:
    total_count: int
    items: tuple[dict[str, Any], ...]
