from dataclasses import dataclass, field
from datetime import date
from typing import TypeAlias

from app.diagnosis.feature_sources import FeatureSource


FeatureValue: TypeAlias = str | int | float | bool | None
FeatureValues: TypeAlias = dict[str, FeatureValue]


@dataclass(frozen=True)
class FeatureInput:
    contract_date: date
    normalized_address: str
    district: str
    housing_type: str

    property_detail: FeatureValues = field(
        default_factory=dict
    )
    property_match: FeatureValues = field(
        default_factory=dict
    )
    building_ledger: FeatureValues = field(
        default_factory=dict
    )
    rone: FeatureValues = field(
        default_factory=dict
    )
    cofix: FeatureValues = field(
        default_factory=dict
    )
    ecos: FeatureValues = field(
        default_factory=dict
    )
    kosis: FeatureValues = field(
        default_factory=dict
    )

    def values_for(
        self,
        source: FeatureSource,
    ) -> FeatureValues:
        source_values = {
            FeatureSource.ADDRESS: {
                "시군구": self.district,
            },
            FeatureSource.PROPERTY_RESOLVER: {
                "주택유형": self.housing_type,
            },
            FeatureSource.PROPERTY_DETAIL: self.property_detail,
            FeatureSource.PROPERTY_MATCH: self.property_match,
            FeatureSource.BUILDING_LEDGER: self.building_ledger,
            FeatureSource.RONE: self.rone,
            FeatureSource.COFIX: self.cofix,
            FeatureSource.ECOS: self.ecos,
            FeatureSource.KOSIS: self.kosis,
        }

        return source_values.get(source, {})