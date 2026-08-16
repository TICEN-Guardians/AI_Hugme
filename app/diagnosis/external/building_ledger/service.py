from dataclasses import dataclass
from typing import Any

from app.diagnosis.external.building_ledger.client import (BuildingLedgerClient,)
from app.diagnosis.external.building_ledger.mapper import (BuildingLedgerMapper,)
from app.diagnosis.external.building_ledger.schemas import (BuildingLedgerKey,)
from app.diagnosis.external.building_ledger.selector import (BuildingLedgerSelector,)
from app.diagnosis.feature_input import FeatureValues
from app.diagnosis.external.building_ledger.unit_area import (UnitAreaMapper,UnitAreaResult,)
from app.diagnosis.external.building_ledger.quality import (BuildingLedgerQuality,BuildingLedgerQualityGate,)


@dataclass(frozen=True)
class BuildingLedgerResult:
    feature_values: FeatureValues
    selected_title: dict[str, Any]
    title_count: int
    quality: BuildingLedgerQuality


class BuildingLedgerService:
    def __init__(
        self,
        client: BuildingLedgerClient,
    ) -> None:
        self.client = client

    def fetch(
        self,
        key: BuildingLedgerKey,
        building_name: str,
        dong_name: str,
    ) -> BuildingLedgerResult:
        titles = self.client.get_title(key)

        selected = BuildingLedgerSelector.select_title(
            items=titles,
            building_name=building_name,
            dong_name=dong_name,
        )

        feature_values = (
            BuildingLedgerMapper.map_title(selected)
        )
        quality = BuildingLedgerQualityGate.evaluate(
            selected
        )

        return BuildingLedgerResult(
            feature_values=feature_values,
            selected_title=selected,
            title_count=len(titles),
            quality=quality,
        )

    def fetch_unit_area(
        self,
        key: BuildingLedgerKey,
        dong_name: str,
        ho_name: str,
    ) -> UnitAreaResult:
        items = self.client.get_exclusive_area(
            key=key,
            dong_name=dong_name,
            ho_name=ho_name,
        )

        return UnitAreaMapper.map(
            items=items,
            dong_name=dong_name,
            ho_name=ho_name,
        )