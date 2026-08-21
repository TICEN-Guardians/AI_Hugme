import unittest

from app.ocr.registry_resolver import resolve_registry_extraction
from tests.test_registry_resolver import PAGE_ONE, PAGE_TWO, extraction


class RegistryResolverSafetyTest(unittest.TestCase):
    def test_unverified_llm_right_prevents_success_status(self):
        value = extraction().model_copy(deep=True)
        value.rights.append(type(value.rights[0]).model_validate({
            "section": "갑구",
            "rank_no": "99",
            "purpose": "압류",
            "receipt_no": "제999999호",
            "registered_at": None,
            "holder": None,
            "debtor": None,
            "amount": None,
            "target_rank_nos": [],
            "joint_collateral_id": None,
        }))

        result = resolve_registry_extraction(value, (PAGE_ONE, PAGE_TWO))

        self.assertEqual("NEEDS_REVIEW", result["parse_status"])
        self.assertEqual("MEDIUM", result["parse_confidence"])

    def test_land_or_general_building_never_uses_legal_dong_as_unit_dong(self):
        value = extraction().model_copy(deep=True)
        building_page = PAGE_ONE.replace("[집합건물]", "[건물]")

        result = resolve_registry_extraction(value, (building_page, PAGE_TWO))

        self.assertIsNone(result["dong_name"])
        self.assertIsNone(result["floor"])
        self.assertIsNone(result["ho_name"])
        self.assertIsNone(result["exclusive_area"])


if __name__ == "__main__":
    unittest.main()
