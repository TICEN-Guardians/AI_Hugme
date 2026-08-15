import argparse

from app.config import settings
from app.diagnosis.external.building_ledger.client import (
    BuildingLedgerClient,
)
from app.diagnosis.external.building_ledger.mapper import (
    BuildingLedgerMapper,
)
from app.diagnosis.external.building_ledger.schemas import (
    BuildingLedgerKey,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument("--sigungu-code", required=True)
    parser.add_argument("--bjdong-code", required=True)
    parser.add_argument("--plat-code", default="0")
    parser.add_argument("--bun", required=True)
    parser.add_argument("--ji", default="0000")

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not settings.building_ledger_api_key:
        raise ValueError(
            "BUILDING_LEDGER_API_KEY 환경변수 누락"
        )

    key = BuildingLedgerKey(
        sigungu_code=args.sigungu_code,
        bjdong_code=args.bjdong_code,
        plat_code=args.plat_code,
        bun=args.bun.zfill(4),
        ji=args.ji.zfill(4),
    )

    client = BuildingLedgerClient(
        service_key=settings.building_ledger_api_key,
        timeout=settings.building_ledger_api_timeout,
    )

    items = client.get_title(key)

    print(f"표제부 조회 완료: {len(items)}건")

    if not items:
        print("조회 결과 없음")
        return

    print("첫 번째 응답 필드:")
    print(sorted(items[0].keys()))

    mapped = BuildingLedgerMapper.map_title(items[0])

    print("첫 번째 표제부 Feature:")
    for name, value in mapped.items():
        print(f"- {name}: {value}")


if __name__ == "__main__":
    main()