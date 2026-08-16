from app.diagnosis.external.address.mapper import (
    AddressMapper,
)


def main() -> None:
    item = {
        "roadAddr": (
            "서울특별시 강남구 테스트로 12 "
            "(테스트동, 테스트아파트)"
        ),
        "jibunAddr": (
            "서울특별시 강남구 테스트동 123-4 "
            "테스트아파트"
        ),
        "admCd": "1168010300",
        "siNm": "서울특별시",
        "sggNm": "강남구",
        "emdNm": "테스트동",
        "liNm": "",
        "lnbrMnnm": "123",
        "lnbrSlno": "4",
        "mtYn": "0",
        "bdNm": "테스트아파트",
        "detBdNmList": "101동,102동,상가동",
    }

    result = AddressMapper.map_result(item)
    key = result.building_ledger_key

    assert result.legal_dong_code == "1168010300"
    assert result.district == "서울특별시 강남구 테스트동"
    assert result.building_name == "테스트아파트"
    assert result.available_dongs == (
        "101동",
        "102동",
        "상가동",
    )

    assert key.sigungu_code == "11680"
    assert key.bjdong_code == "10300"
    assert key.plat_code == "0"
    assert key.bun == "0123"
    assert key.ji == "0004"

    mountain = {
        **item,
        "mtYn": "1",
        "lnbrSlno": "0",
    }

    mountain_result = AddressMapper.map_result(
        mountain
    )

    assert (
        mountain_result.building_ledger_key.plat_code
        == "1"
    )
    assert (
        mountain_result.building_ledger_key.ji
        == "0000"
    )

    print("주소 Mapper 검증 완료")
    print("- 법정동코드 분리")
    print("- 본번·부번 변환")
    print("- 대지·산 구분")
    print("- 건물명·동 후보 변환")


if __name__ == "__main__":
    main()