import unittest
from datetime import date

from app.diagnosis.external.rtms.client import RtmsApiError, RtmsClient
from app.diagnosis.external.rtms.schemas import RentTransaction
from app.diagnosis.external.rtms.service import MarketComparableService
from app.diagnosis.schemas import HousingType


class FakeResponse:
    def __init__(self, content: bytes) -> None:
        self.content = content

    def raise_for_status(self) -> None:
        return None


class FakeSession:
    def __init__(self, content: bytes) -> None:
        self.content = content
        self.calls = 0

        self.service_keys = []
    def get(self, url, params, timeout):
        self.calls += 1
        self.service_keys.append(params["serviceKey"])
        return FakeResponse(self.content)


class FakeRtmsClient:
    def __init__(self, transactions):
        self.transactions = transactions

    def get_rent_transactions(self, housing_type, district_code, deal_ym):
        return tuple(
            item
            for item in self.transactions
            if item.contract_date.strftime("%Y%m") == deal_ym
        )



class RtmsClientTest(unittest.TestCase):
    def test_reads_only_active_jeonse_transactions(self):
        payload = """<?xml version="1.0" encoding="UTF-8"?>
        <response>
          <header><resultCode>000</resultCode><resultMsg>OK</resultMsg></header>
          <body>
            <totalCount>3</totalCount>
            <items>
              <item>
                <deposit>20,000</deposit>
                <monthlyRent>0</monthlyRent>
                <excluUseAr>59.8</excluUseAr>
                <dealYear>2026</dealYear>
                <dealMonth>6</dealMonth>
                <dealDay>4</dealDay>
                <umdNm>화서동</umdNm>
                <aptNm>화서아파트</aptNm>
              </item>
              <item>
                <deposit>5,000</deposit>
                <monthlyRent>45</monthlyRent>
                <excluUseAr>59.8</excluUseAr>
                <dealYear>2026</dealYear>
                <dealMonth>6</dealMonth>
                <dealDay>5</dealDay>
              </item>
              <item>
                <deposit>21,000</deposit>
                <monthlyRent>0</monthlyRent>
                <excluUseAr>59.8</excluUseAr>
                <dealYear>2026</dealYear>
                <dealMonth>6</dealMonth>
                <dealDay>6</dealDay>
                <cdealDay>20260701</cdealDay>
              </item>
            </items>
          </body>
        </response>""".encode("utf-8")
        session = FakeSession(payload)
        client = RtmsClient(
            {HousingType.APARTMENT: "test%2Bkey%2Fvalue%3D"},
            session=session,
        )

        result = client.get_rent_transactions(
            HousingType.APARTMENT,
            "41110",
            "202606",
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].deposit, 200_000_000)
        self.assertEqual(result[0].area, 59.8)
        self.assertEqual(result[0].legal_dong, "화서동")
        self.assertEqual(result[0].building_name, "화서아파트")

        self.assertEqual(session.service_keys, ["test+key/value="])
    def test_rejects_unapproved_service_key_without_retry(self):
        payload = """<?xml version="1.0" encoding="UTF-8"?>
        <OpenAPI_ServiceResponse>
          <cmmMsgHeader>
            <returnReasonCode>30</returnReasonCode>
            <returnAuthMsg>SERVICE_KEY_IS_NOT_REGISTERED_ERROR</returnAuthMsg>
          </cmmMsgHeader>
        </OpenAPI_ServiceResponse>""".encode("utf-8")
        session = FakeSession(payload)
        client = RtmsClient(
            {HousingType.APARTMENT: "test-key"},
            session=session,
        )

        with self.assertRaises(RtmsApiError):
            client.get_rent_transactions(
                HousingType.APARTMENT,
                "41110",
                "202606",
            )

        self.assertEqual(session.calls, 1)


class MarketComparableServiceTest(unittest.TestCase):
    def test_prioritizes_same_building_and_summarizes_distribution(self):
        deposits = [
            100_000_000,
            110_000_000,
            120_000_000,
            130_000_000,
            140_000_000,
            150_000_000,
        ]
        transactions = tuple(
            RentTransaction(
                deposit=deposit,
                area=59.8 + index * 0.1,
                contract_date=date(2026, index + 1, 10),
                legal_dong="화서동",
                building_name="화서 아파트",
            )
            for index, deposit in enumerate(deposits)
        )
        service = MarketComparableService(
            FakeRtmsClient(transactions)
        )

        result = service.analyze(
            housing_type=HousingType.APARTMENT,
            district_code="41110",
            district="경기도 수원시 팔달구 화서동",
            building_name="화서아파트",
            area=59.8,
            contract_date=date(2026, 6, 30),
            user_deposit=135_000_000,
        )

        self.assertEqual(result.status, "AVAILABLE")
        self.assertEqual(result.scope, "SAME_BUILDING")
        self.assertEqual(result.sample_count, 6)
        self.assertEqual(result.percentile_25, 112_500_000)
        self.assertEqual(result.median, 125_000_000)
        self.assertEqual(result.percentile_75, 137_500_000)
        self.assertEqual(result.user_deposit_percentile, 66.7)
        self.assertEqual(sum(item.count for item in result.bins), 6)


if __name__ == "__main__":
    unittest.main()
