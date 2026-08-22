import unittest

from app.ocr.registry_merge import RegistryMergeError, merge_registry_results


FLAGS = {
    "seizure": "FALSE",
    "provisional_seizure": "FALSE",
    "provisional_disposition": "FALSE",
    "auction_commenced": "FALSE",
    "trust_registration": "FALSE",
    "has_active_jeonse_right": "FALSE",
    "has_leasehold_registration": "FALSE",
}


def result(
    document_type: str,
    address: str = "대전광역시 유성구 덕명동 590-2",
    has_joint_collateral_mention: bool = True,
) -> dict:
    mortgage = {
        "rank_no": "1",
        "receipt_no": "제100호" if document_type == "BUILDING" else "제200호",
        "registered_at": "2020-01-02",
        "creditor": "한국은행",
        "debtor": "홍길동",
        "max_claim_amount": 650000000,
        "status": "ACTIVE",
    }
    return {
        "parse_status": "SUCCESS",
        "parse_confidence": "HIGH",
        "document_type": document_type,
        "property_address": address,
        "issue_date": "2026-08-21",
        "dong_name": None,
        "floor": None,
        "ho_name": None,
        "exclusive_area": None,
        "current_owners": [{
            "name": "홍길동",
            "jumin_front": "800101",
            "address": "대전광역시 유성구",
            "share": "1/1",
            "status": "CURRENT",
            "age": None,
        }],
        "ownership_history": [],
        "has_cancellation_mention": False,
        "has_joint_collateral_mention": has_joint_collateral_mention,
        "registry_rights": {
            "gap_section_status": "EXTRACTED",
            "eul_section_status": "EXTRACTED",
            "rights": [],
            "mortgages": [mortgage],
            "jeonse_rights": [],
            "leasehold_registrations": [],
            "mortgage_link_signatures": {},
            "flags": dict(FLAGS),
            "active_mortgage_count": 1,
            "total_active_max_claim_amount": 650000000,
            "llm_right_count": 1,
            "verified_right_count": 1,
        },
    }


class RegistryMergeTest(unittest.TestCase):
    def test_land_and_building_common_claim_is_not_summed_twice(self):
        merged = merge_registry_results(
            [result("BUILDING"), result("LAND")],
            ["building.pdf", "land.pdf"],
        )

        self.assertEqual(1, merged["registry_rights"]["active_mortgage_count"])
        self.assertEqual(
            650000000,
            merged["registry_rights"]["total_active_max_claim_amount"],
        )

    def test_common_amendment_deduplicates_joint_collateral_with_changed_debtor(self):
        building = result("BUILDING")
        land = result("LAND")
        building_mortgage = building["registry_rights"]["mortgages"][0]
        land_mortgage = land["registry_rights"]["mortgages"][0]
        building_mortgage["creditor"] = None
        building_mortgage["debtor"] = "이은원"
        land_mortgage["debtor"] = "이상희"
        signature = [("2025-11-03", "제5755588호", 132000000)]
        building["registry_rights"]["mortgage_link_signatures"] = {"1": signature}
        land["registry_rights"]["mortgage_link_signatures"] = {"1": signature}
        building_mortgage["max_claim_amount"] = 132000000
        land_mortgage["max_claim_amount"] = 132000000

        merged = merge_registry_results(
            [building, land],
            ["building.pdf", "land.pdf"],
        )

        self.assertEqual(
            1,
            merged["registry_rights"]["active_mortgage_count"],
        )
        self.assertEqual(
            132000000,
            merged["registry_rights"]["total_active_max_claim_amount"],
        )

    def test_common_amendment_without_repeated_amount_uses_current_amount(self):
        building = result("BUILDING")
        land = result("LAND")
        signature = [("2026-04-30", "제2417520호", None)]
        building["registry_rights"]["mortgage_link_signatures"] = {"1": signature}
        land["registry_rights"]["mortgage_link_signatures"] = {"1": signature}

        merged = merge_registry_results(
            [building, land],
            ["building.pdf", "land.pdf"],
        )

        self.assertEqual(
            1,
            merged["registry_rights"]["active_mortgage_count"],
        )

    def test_rejects_documents_for_different_properties(self):
        with self.assertRaises(RegistryMergeError) as raised:
            merge_registry_results(
                [result("BUILDING"), result("LAND", "다른 주소")],
                ["building.pdf", "land.pdf"],
            )

        self.assertEqual("REGISTRY_PROPERTY_MISMATCH", raised.exception.code)

    def test_same_parties_and_amount_are_not_merged_without_common_collateral(self):
        merged = merge_registry_results(
            [
                result("BUILDING", has_joint_collateral_mention=False),
                result("LAND", has_joint_collateral_mention=False),
            ],
            ["building.pdf", "land.pdf"],
        )

        self.assertEqual(2, merged["registry_rights"]["active_mortgage_count"])
        self.assertEqual(
            1300000000,
            merged["registry_rights"]["total_active_max_claim_amount"],
        )

    def test_same_receipt_number_on_different_dates_is_not_merged(self):
        building = result("BUILDING", has_joint_collateral_mention=False)
        land = result("LAND", has_joint_collateral_mention=False)
        land_mortgage = land["registry_rights"]["mortgages"][0]
        land_mortgage["receipt_no"] = "제100호"
        land_mortgage["registered_at"] = "2021-01-02"

        merged = merge_registry_results(
            [building, land],
            ["building.pdf", "land.pdf"],
        )

        self.assertEqual(2, merged["registry_rights"]["active_mortgage_count"])
        self.assertEqual(
            1300000000,
            merged["registry_rights"]["total_active_max_claim_amount"],
        )

    def test_rejects_two_documents_of_the_same_type(self):
        with self.assertRaises(RegistryMergeError) as raised:
            merge_registry_results(
                [result("LAND"), result("LAND")],
                ["first.pdf", "second.pdf"],
            )

        self.assertEqual("REGISTRY_DOCUMENT_SET_INVALID", raised.exception.code)


if __name__ == "__main__":
    unittest.main()
