from app.diagnosis.external.address.schemas import (
    AddressSearchResult,
)
from app.diagnosis.external.address.service import (
    AddressResolutionError,
    AddressService,
)


class FakeClient:
    def __init__(
        self,
        result: AddressSearchResult,
    ) -> None:
        self.result = result

    def search(
        self,
        keyword: str,
    ) -> AddressSearchResult:
        assert keyword
        return self.result


def address_item() -> dict:
    return {
        "roadAddr": (
            "서울특별시 강남구 개포로 516 "
            "(개포동, 개포주공아파트)"
        ),
        "jibunAddr": (
            "서울특별시 강남구 개포동 185 "
            "개포주공아파트"
        ),
        "admCd": "1168010300",
        "siNm": "서울특별시",
        "sggNm": "강남구",
        "emdNm": "개포동",
        "liNm": "",
        "lnbrMnnm": "185",
        "lnbrSlno": "0",
        "mtYn": "0",
        "bdNm": "개포주공아파트",
        "detBdNmList": "101동,102동",
    }


def main() -> None:
    success_service = AddressService(
        client=FakeClient(
            AddressSearchResult(
                total_count=1,
                items=(address_item(),),
            )
        )
    )

    resolved = success_service.resolve(
        "서울특별시 강남구 개포로 516"
    )

    key = resolved.building_ledger_key

    assert resolved.building_name == "개포주공아파트"
    assert resolved.available_dongs == (
        "101동",
        "102동",
    )
    assert key.sigungu_code == "11680"
    assert key.bjdong_code == "10300"
    assert key.plat_code == "0"
    assert key.bun == "0185"
    assert key.ji == "0000"

    multiple_service = AddressService(
        client=FakeClient(
            AddressSearchResult(
                total_count=2,
                items=(
                    address_item(),
                    address_item(),
                ),
            )
        )
    )

    try:
        multiple_service.resolve("개포로")
    except AddressResolutionError:
        pass
    else:
        raise AssertionError(
            "복수 주소 차단 실패"
        )

    print("주소 Service 검증 완료")
    print("- 단일 주소 확정")
    print("- 건축물대장 조회 키 생성")
    print("- 복수 주소 차단")


if __name__ == "__main__":
    main()
