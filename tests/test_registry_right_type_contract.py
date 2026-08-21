import unittest

from app.ocr.registry_text_rules import classify_right_kind


class RegistryRightTypeContractTest(unittest.TestCase):
    def test_mortgage_transfer_is_classified_explicitly(self):
        kind = classify_right_kind(
            "1 근저당권이전 2026년 1월 2일 제123호"
        )

        self.assertEqual("MORTGAGE_TRANSFER", kind)

    def test_provisional_registration_is_classified_explicitly(self):
        kind = classify_right_kind(
            "2 소유권이전청구권가등기 2026년 1월 3일 제124호"
        )

        self.assertEqual("PROVISIONAL_REGISTRATION", kind)


if __name__ == "__main__":
    unittest.main()
