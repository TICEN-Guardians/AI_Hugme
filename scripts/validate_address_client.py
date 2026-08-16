from typing import Any

from app.diagnosis.external.address.client import (
    AddressClient,
)


class FakeResponse:
    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict[str, Any]:
        return {
            "results": {
                "common": {
                    "errorCode": "0",
                    "errorMessage": "정상",
                    "totalCount": "2",
                },
                "juso": [
                    {
                        "roadAddr": "서울시 테스트로 12",
                        "jibunAddr": "서울시 테스트동 123",
                        "admCd": "1168010300",
                    },
                    {
                        "roadAddr": "서울시 테스트로 14",
                        "jibunAddr": "서울시 테스트동 124",
                        "admCd": "1168010300",
                    },
                ],
            }
        }


class FakeSession:
    def get(
        self,
        url: str,
        params: dict[str, str],
        timeout: float,
    ) -> FakeResponse:
        assert url.endswith("/addrLinkApi.do")
        assert params["confmKey"] == "test-key"
        assert params["keyword"] == "서울시 테스트로"
        assert params["resultType"] == "json"
        assert params["countPerPage"] == "100"
        assert timeout == 10.0

        return FakeResponse()


def main() -> None:
    client = AddressClient(
        confirmation_key="test-key",
        session=FakeSession(),
    )

    result = client.search(
        "서울시 테스트로"
    )

    assert result.total_count == 2
    assert len(result.items) == 2

    assert (
        result.items[0]["roadAddr"]
        == "서울시 테스트로 12"
    )
    assert (
        result.items[1]["roadAddr"]
        == "서울시 테스트로 14"
    )

    print("주소 Client 검증 완료")
    print("- 검색 요청 검증")
    print("- 복수 결과 유지")
    print("- 임의 선택 없음")


if __name__ == "__main__":
    main()