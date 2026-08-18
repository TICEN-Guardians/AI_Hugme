from datetime import date

from app.diagnosis.feature_builder import FeatureBuilder
from app.diagnosis.feature_contract import load_feature_contract
from app.diagnosis.feature_input import FeatureInput
from app.diagnosis.feature_sources import (
    FeatureSource,
    get_feature_source,
)


def main() -> None:
    contract = load_feature_contract()
    builder = FeatureBuilder(contract)

    for model in contract.models.values():
        grouped = {
            source: {}
            for source in FeatureSource
        }

        for name in model.features:
            source = get_feature_source(name)

            if source == FeatureSource.DERIVED:
                continue

            value = (
                "UNKNOWN"
                if name in model.categorical_features
                else 1.0
            )

            grouped[source][name] = value

        building = grouped[
            FeatureSource.BUILDING_LEDGER
        ]
        building["사용승인연도"] = 2010
        building.setdefault("연면적(㎡)", 100.0)
        building.setdefault("대지면적(㎡)", 50.0)

        feature_input = FeatureInput(
            contract_date=date(2026, 8, 15),
            normalized_address="테스트 주소",
            district="서울특별시 강남구",
            housing_type="APARTMENT",
            property_detail=grouped[
                FeatureSource.PROPERTY_DETAIL
            ],
            property_match=grouped[
                FeatureSource.PROPERTY_MATCH
            ],
            building_ledger=building,
            rone=grouped[FeatureSource.RONE],
            cofix=grouped[FeatureSource.COFIX],
            ecos=grouped[FeatureSource.ECOS],
            kosis=grouped[FeatureSource.KOSIS],
        )

        result = builder.build(
            model.model_key,
            feature_input,
        )

        assert result.names == model.features
        assert len(result.values) == model.feature_count
        assert None not in result.values

        print(
            f"- {model.model_key}: "
            f"{len(result.values)} features"
        )

    print("FeatureBuilder 검증 완료")


if __name__ == "__main__":
    main()