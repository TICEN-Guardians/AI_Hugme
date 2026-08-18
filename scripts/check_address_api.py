import argparse

from app.config import settings
from app.diagnosis.external.address.client import (
    AddressClient,
)
from app.diagnosis.external.address.mapper import (
    AddressMapper,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--keyword",
        required=True,
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not settings.address_api_confirmation_key:
        raise ValueError(
            "ADDRESS_API_CONFIRMATION_KEY 환경변수 누락"
        )

    client = AddressClient(
        confirmation_key=(
            settings.address_api_confirmation_key
        ),
        timeout=settings.address_api_timeout,
    )

    result = client.search(args.keyword)

    print(f"주소 검색 완료: {result.total_count}건")

    for index, item in enumerate(result.items):
        print(
            f"- [{index}] "
            f"{item.get('roadAddr')} / "
            f"{item.get('jibunAddr')} / "
            f"{item.get('bdNm')}"
        )

    if result.total_count != 1:
        print("주소 단일 확정 불가")
        return

    resolved = AddressMapper.map_result(
        result.items[0]
    )

    print("주소 변환 완료")
    print(f"- 도로명주소: {resolved.road_address}")
    print(f"- 지번주소: {resolved.jibun_address}")
    print(f"- 법정동코드: {resolved.legal_dong_code}")
    print(f"- 시군구: {resolved.district}")
    print(f"- 건물명: {resolved.building_name}")
    print(f"- 동 후보: {resolved.available_dongs}")
    print(
        "- 건축물대장 조회 키: "
        f"{resolved.building_ledger_key}"
    )


if __name__ == "__main__":
    main()