import unittest
from unittest.mock import patch

import requests

from app.diagnosis.external.building_ledger.client import BuildingLedgerClient
from app.diagnosis.external.building_ledger.schemas import BuildingLedgerKey


class FakeResponse:
    def __init__(self, payload=None, error=None) -> None:
        self.payload = payload
        self.error = error

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        if self.error is not None:
            raise self.error
        return self.payload


class FakeSession:
    def __init__(self, responses) -> None:
        self.responses = list(responses)
        self.calls = 0

    def get(self, url, params, timeout):
        response = self.responses[self.calls]
        self.calls += 1
        if isinstance(response, Exception):
            raise response
        return response


class BuildingLedgerClientTest(unittest.TestCase):
    @patch(
        "app.diagnosis.external.building_ledger.client.time.sleep",
        return_value=None,
    )
    def test_recovers_after_three_invalid_json_responses(self, sleep) -> None:
        invalid = requests.exceptions.JSONDecodeError(
            "invalid response",
            "not-json",
            0,
        )
        payload = {
            "response": {
                "header": {
                    "resultCode": "00",
                    "resultMsg": "NORMAL SERVICE",
                },
                "body": {
                    "items": {
                        "item": [{"bldNm": "테스트 건물"}],
                    },
                },
            },
        }
        session = FakeSession([
            FakeResponse(error=invalid),
            FakeResponse(error=invalid),
            FakeResponse(error=invalid),
            FakeResponse(payload=payload),
        ])
        client = BuildingLedgerClient(
            service_key="test-key",
            session=session,
        )
        key = BuildingLedgerKey(
            sigungu_code="11110",
            bjdong_code="10100",
            plat_code="0",
            bun="0001",
            ji="0000",
        )

        result = client.get_title(key)

        self.assertEqual(result, [{"bldNm": "테스트 건물"}])
        self.assertEqual(session.calls, 4)
        self.assertEqual(sleep.call_count, 3)

    @patch(
        "app.diagnosis.external.building_ledger.client.time.sleep",
        return_value=None,
    )
    def test_limits_connection_error_retries(self, sleep) -> None:
        session = FakeSession([
            requests.ConnectionError("temporary failure"),
            requests.ConnectionError("temporary failure"),
            requests.ConnectionError("temporary failure"),
        ])
        client = BuildingLedgerClient(
            service_key="test-key",
            session=session,
        )
        key = BuildingLedgerKey(
            sigungu_code="11110",
            bjdong_code="10100",
            plat_code="0",
            bun="0001",
            ji="0000",
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "건축물대장 API 호출 실패",
        ):
            client.get_title(key)

        self.assertEqual(session.calls, 3)
        self.assertEqual(sleep.call_count, 2)


if __name__ == "__main__":
    unittest.main()