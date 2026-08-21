import unittest

from app.ocr.registry_llm import RegistryLlmExtraction
from app.ocr.registry_resolver import resolve_registry_extraction


PAGE_ONE = """
[집합건물] 경기도 수원시 예시로 1 제3층 제302호
전유부분 59.83㎡
【갑구】
소유자 노진현 900101-******* 지분 2분의 1 수원시
소유자 현주 920202-******* 지분 2분의 1 수원시
"""

PAGE_TWO = """
【을구】
1 근저당권설정 2024년 1월 2일 제100호 채권최고액 금100,000,000원 근저당권자 은행
1-1 1번근저당권설정등기 변경 2025년 2월 3일 제101호 채권최고액 금81,600,000원
6 전세권설정 2020년 1월 1일 제200호 전세금 금50,000,000원 기간 2020년 1월 1일까지
열람일시 : 2026년 8월 21일
"""


def extraction() -> RegistryLlmExtraction:
    return RegistryLlmExtraction.model_validate({
        "property_address": "경기도 수원시 예시로 1 제3층 제302호",
        "issue_date": "2026-08-21",
        "unit": {
            "dong_name": None,
            "floor": "3",
            "ho_name": "302",
            "exclusive_area_sqm": "59.83",
        },
        "current_owners": [
            {"name": "노진현", "jumin_front": "900101-*******", "address": "수원시",
             "share": "1/2"},
            {"name": "현주", "jumin_front": "920202-*******", "address": "수원시",
             "share": "1/2"},
        ],
        "ownership_history": [],
        "rights": [
            {"section": "을구", "rank_no": "1", "purpose": "근저당권설정",
             "receipt_no": "제100호", "registered_at": "2024-01-02", "holder": "은행",
             "debtor": None, "amount": 100000000, "target_rank_nos": [],
             "joint_collateral_id": None},
            {"section": "을구", "rank_no": "1-1", "purpose": "1번근저당권설정등기 변경",
             "receipt_no": "제101호", "registered_at": "2025-02-03", "holder": None,
             "debtor": None, "amount": 81600000, "target_rank_nos": ["1"],
             "joint_collateral_id": None},
            {"section": "을구", "rank_no": "6", "purpose": "전세권설정",
             "receipt_no": "제200호", "registered_at": "2020-01-01", "holder": None,
             "debtor": None, "amount": 50000000, "target_rank_nos": [],
             "joint_collateral_id": None},
        ],
    })


class RegistryResolverTest(unittest.TestCase):
    def test_finds_rights_on_their_actual_page_without_model_page_numbers(self):
        result = resolve_registry_extraction(extraction(), (PAGE_ONE, PAGE_TWO))

        rights = result["registry_rights"]
        self.assertEqual(81600000, rights["total_active_max_claim_amount"])
        self.assertEqual("ACTIVE", rights["jeonse_rights"][0]["status"])
        self.assertEqual(["1/2", "1/2"], [owner["share"] for owner in result["current_owners"]])
        self.assertTrue(all(right["raw_text"].startswith("[PAGE 2]") for right in rights["rights"]))

    def test_cancellation_uses_target_found_in_purpose(self):
        value = extraction().model_copy(deep=True)
        value.rights.append(type(value.rights[0]).model_validate({
            "section": "을구", "rank_no": "9", "purpose": "1번근저당권설정등기말소",
            "receipt_no": "제300호", "registered_at": None, "holder": None, "debtor": None,
            "amount": None, "target_rank_nos": ["1"], "joint_collateral_id": None,
        }))
        page_two = PAGE_TWO.replace(
            "열람일시",
            "9 1번근저당권설정등기말소 제300호\n열람일시",
        )

        result = resolve_registry_extraction(value, (PAGE_ONE, page_two))

        self.assertEqual(0, result["registry_rights"]["active_mortgage_count"])
        self.assertEqual(0, result["registry_rights"]["total_active_max_claim_amount"])

    def test_missing_eul_entries_never_becomes_false_zero_mortgage(self):
        value = extraction().model_copy(deep=True)
        value.rights = []

        result = resolve_registry_extraction(value, (PAGE_ONE, PAGE_TWO))

        self.assertEqual("PARSE_FAILED", result["registry_rights"]["eul_section_status"])
        self.assertIsNone(result["registry_rights"]["active_mortgage_count"])
        self.assertIsNone(result["registry_rights"]["total_active_max_claim_amount"])
        self.assertEqual("UNKNOWN", result["registry_rights"]["flags"]["has_active_jeonse_right"])

    def test_discards_owner_values_not_found_together_in_the_pdf(self):
        value = extraction().model_copy(deep=True)
        value.current_owners[0].name = "문서에없는사람"

        result = resolve_registry_extraction(value, (PAGE_ONE, PAGE_TWO))

        self.assertEqual(["현주"], [owner["name"] for owner in result["current_owners"]])
        self.assertEqual("PARTIAL", result["parse_status"])
        self.assertEqual("LOW", result["parse_confidence"])


if __name__ == "__main__":
    unittest.main()
