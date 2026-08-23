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

    def test_condominium_never_uses_legal_dong_as_building_unit(self):
        value = extraction().model_copy(deep=True)
        property_address = (
            "인천광역시 미추홀구 주안동 75-89 스타캐슬 제6층 제602호"
        )
        value.property_address = property_address
        value.unit.dong_name = "주안"
        value.unit.floor = "6"
        value.unit.ho_name = "602"
        page_one = PAGE_ONE.replace(
            "경기도 수원시 예시로 1 제3층 제302호",
            property_address,
        )

        result = resolve_registry_extraction(value, (page_one, PAGE_TWO))

        self.assertIsNone(result["dong_name"])
        self.assertEqual(6, result["floor"])
        self.assertEqual("602", result["ho_name"])
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
