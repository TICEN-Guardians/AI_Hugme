from datetime import date

from app.diagnosis.feature_input import FeatureInput
from app.diagnosis.feature_sources import FeatureSource


def main() -> None:
    feature_input = FeatureInput(
        contract_date=date(2026, 8, 15),
        normalized_address=(
            "서울특별시 강남구 테헤란로 123"
        ),
        district="서울특별시 강남구",
        housing_type="APARTMENT",
        property_detail={
            "전용면적(㎡)": 84.52,
            "층": 12,
        },
        property_match={
            "단지명": "테스트아파트",
        },
        building_ledger={
            "건축물대장_원천_표제부_최고지상층수": 25,
        },
        rone={
            "RONE_가격지수": 98.4,
        },
        cofix={
            "신규취급액기준_COFIX": 3.42,
        },
        ecos={
            "ECOS_주담대금리_적용값": 4.1,
        },
        kosis={
            "KOSIS_경제심리지수": 92.3,
        },
    )

    address_values = feature_input.values_for(
        FeatureSource.ADDRESS
    )
    building_values = feature_input.values_for(
        FeatureSource.BUILDING_LEDGER
    )

    assert address_values["시군구"] == (
        "서울특별시 강남구"
    )
    assert (
        building_values[
            "건축물대장_원천_표제부_최고지상층수"
        ]
        == 25
    )

    print("FeatureInput 검증 완료")


if __name__ == "__main__":
    main()