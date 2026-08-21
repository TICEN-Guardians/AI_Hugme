import unittest

from app.diagnosis.external.address.client import AddressClient


class FakeResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {
            "results": {
                "common": {
                    "errorCode": "0",
                    "totalCount": "1",
                },
                "juso": [{"roadAddr": "서울특별시 중구 세종대로 110"}],
            }
        }


class FakeSession:
    def __init__(self) -> None:
        self.params = None

    def get(self, url, params, timeout):
        self.params = params
        return FakeResponse()


class AddressSuggestionsTest(unittest.TestCase):
    def test_requests_ten_items(self) -> None:
        session = FakeSession()
        client = AddressClient(
            confirmation_key="test-key",
            session=session,
        )

        result = client.search("세종대로", count_per_page=10)

        self.assertEqual(result.total_count, 1)
        self.assertEqual(session.params["countPerPage"], "10")
