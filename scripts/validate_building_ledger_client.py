from typing import Any

from app.diagnosis.external.building_ledger.client import (
    BuildingLedgerClient,
)
from app.diagnosis.external.building_ledger.schemas import (
    BuildingLedgerKey,
)


class FakeResponse:
    def __init__(self, endpoint: str) -> None:
        self.endpoint = endpoint

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict[str, Any]:
        item = {
            "bldNm": "테스트 건물",
            "totArea": 1234.5,
            "platArea": 500.0,
            "useAprDay": "20150312",
            "endpoint": self.endpoint,
        }

        return {
            "response": {
                "header": {
                    "resultCode": "00",
                    "resultMsg": "NORMAL SERVICE",
                },
                "body": {
                    "items": {
                        "item": item,
                    }
                },
            }
        }


class FakeSession:
    def get(
        self,
        url: str,
        params: dict[str, str],
        timeout: float,
    ) -> FakeResponse:
        endpoint = url.rsplit("/", 1)[-1]

        assert endpoint in {
            "getBrTitleInfo",
            "getBrRecapTitleInfo",
        }
        assert params["sigunguCd"] == "11680"
        assert params["bjdongCd"] == "10300"
        assert params["bun"] == "0123"
        assert params["ji"] == "0004"
        assert timeout == 10.0

        return FakeResponse(endpoint)


def main() -> None:
    key = BuildingLedgerKey(
        sigungu_code="11680",
        bjdong_code="10300",
        plat_code="0",
        bun="0123",
        ji="0004",
    )

    client = BuildingLedgerClient(
        service_key="test-key",
        session=FakeSession(),
    )

    titles = client.get_title(key)
    recap_titles = client.get_recap_title(key)

    assert len(titles) == 1
    assert titles[0]["endpoint"] == "getBrTitleInfo"

    assert len(recap_titles) == 1
    assert (
        recap_titles[0]["endpoint"]
        == "getBrRecapTitleInfo"
    )

    print("건축물대장 Client 검증 완료")
    print("- 표제부 조회 검증")
    print("- 총괄표제부 조회 검증")


if __name__ == "__main__":
    main()