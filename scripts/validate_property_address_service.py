from app.diagnosis.external.address.schemas import (
    ResolvedAddress,
)
from app.diagnosis.external.building_ledger.schemas import (
    BuildingLedgerKey,
)
from app.diagnosis.external.building_ledger.service import (
    BuildingLedgerResult,
)
from app.diagnosis.external.building_ledger.selector import (
    BuildingLedgerSelectionError,
)
from app.diagnosis.property_address_service import (
    PropertyAddressService,
)
from app.diagnosis.housing_type_resolver import (
    HousingTypeResolutionError,
    HousingTypeResolver,
)
from app.diagnosis.schemas import HousingType

class FakeAddressService:
    def resolve(
        self,
        address: str,
    ) -> ResolvedAddress:
        assert address

        return ResolvedAddress(
            road_address="서울시 테스트로 12",
            jibun_address="서울시 테스트동 185",
            legal_dong_code="1168010300",
            district="서울특별시 강남구 테스트동",
            building_name="테스트아파트",
            available_dongs=(
                "101",
                "102",
                "상가",
            ),
            building_ledger_key=BuildingLedgerKey(
                sigungu_code="11680",
                bjdong_code="10300",
                plat_code="0",
                bun="0185",
                ji="0000",
            ),
        )


class FakeBuildingLedgerService:
    def fetch(
        self,
        key: BuildingLedgerKey,
        building_name: str,
        dong_name: str,
    ) -> BuildingLedgerResult:
        assert key.bun == "0185"
        assert building_name == "테스트아파트"
        assert dong_name == "101동"

        return BuildingLedgerResult(
            feature_values={
                "연면적(㎡)": 1000.0,
                "사용승인연도": 2000,
            },
            selected_title={
                "bldNm": "테스트아파트101동",
                "dongNm": "101",
                "mainPurpsCdNm": "공동주택",
                "etcPurps": "아파트",
            },
            title_count=2,
        )


def main() -> None:
    service = PropertyAddressService(
        address_service=FakeAddressService(),
        building_ledger_service=(
            FakeBuildingLedgerService()
        ),
    )

    result = service.resolve(
        address="서울시 테스트로 12",
        dong_name="101동",
    )

    assert result.dong_name == "101동"
    assert (
        result.address.building_name
        == "테스트아파트"
    )
    assert (
        result.building_ledger.feature_values[
            "연면적(㎡)"
        ]
        == 1000.0
    )
    assert (
        result.building_ledger.selected_title[
            "dongNm"
        ]
        == "101"
    )
    assert (
            result.housing_type
            == HousingType.APARTMENT
    )

    try:
        service.resolve(
            address="서울시 테스트로 12",
            dong_name="999동",
        )
    except BuildingLedgerSelectionError:
        pass
    else:
        raise AssertionError(
            "존재하지 않는 동 차단 실패"
        )
        apartment = HousingTypeResolver.resolve(
            {
                "mainPurpsCdNm": "공동주택",
                "etcPurps": "아파트",
            }
        )
        villa = HousingTypeResolver.resolve(
            {
                "mainPurpsCdNm": "공동주택",
                "etcPurps": "다세대주택",
            }
        )
        officetel = HousingTypeResolver.resolve(
            {
                "mainPurpsCdNm": "업무시설",
                "etcPurps": "오피스텔",
            }
        )
        detached = HousingTypeResolver.resolve(
            {
                "mainPurpsCdNm": "단독주택",
                "etcPurps": "다가구주택",
            }
        )

        assert apartment == HousingType.APARTMENT
        assert villa == HousingType.VILLA
        assert officetel == HousingType.OFFICETEL
        assert detached == HousingType.DETACHED_MULTI

        try:
            HousingTypeResolver.resolve(
                {
                    "mainPurpsCdNm": "공동주택",
                    "etcPurps": "",
                }
            )
        except HousingTypeResolutionError:
            pass
        else:
            raise AssertionError(
                "불명확한 주택유형 차단 실패"
            )

    print("PropertyAddressService 검증 완료")
    print("- 주소 해석 연결")
    print("- 동 후보 검증")
    print("- 건축물대장 조회 연결")
    print("- Feature 변환 결과 수신")
    print("- 주택유형 판정")


if __name__ == "__main__":
    main()