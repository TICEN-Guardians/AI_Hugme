import unittest

from app.ocr.parser import parse_section_entries


class RegistryRightTypeContractTest(unittest.TestCase):
    def test_mortgage_transfer_is_classified_explicitly(self):
        entries = parse_section_entries(
            "1 근저당권이전 2026년 1월 2일 제123호",
            "을구",
        )

        self.assertEqual("MORTGAGE_TRANSFER", entries[0]["kind"])

    def test_provisional_registration_is_classified_explicitly(self):
        entries = parse_section_entries(
            "2 소유권이전청구권가등기 2026년 1월 3일 제124호",
            "갑구",
        )

        self.assertEqual("PROVISIONAL_REGISTRATION", entries[0]["kind"])


if __name__ == "__main__":
    unittest.main()
