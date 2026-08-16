from app.diagnosis.external.address.schemas import (
    ResolvedAddress,
)
from app.diagnosis.external.building_ledger.schemas import (
    BuildingLedgerKey,
)
from app.diagnosis.external.building_ledger.service import (
    BuildingLedgerResult,
)
from app.diagnosis.property_address_service import (
    PropertyAddressError,
    PropertyAddressService,
)


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

    try:
        service.resolve(
            address="서울시 테스트로 12",
            dong_name="999동",
        )
    except PropertyAddressError:
        pass
    else:
        raise AssertionError(
            "존재하지 않는 동 차단 실패"
        )

    print("PropertyAddressService 검증 완료")
    print("- 주소 해석 연결")
    print("- 동 후보 검증")
    print("- 건축물대장 조회 연결")
    print("- Feature 변환 결과 수신")


if __name__ == "__main__":
    main()