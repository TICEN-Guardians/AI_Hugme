import unittest

from app.ocr.document_validator import validate_registry_document


VALID_REGISTRY_TEXT = """
등기사항전부증명서(말소사항 포함)
고유번호 1234-5678-001234
[집합건물] 서울특별시 중구 예시동 1-2 제3층 제301호
【 표 제 부 】
표시번호 접수 소재지번 및 건물번호 건물내역 등기원인 및 기타사항
【 갑 구 】 (소유권에 관한 사항)
순위번호 등기목적 접수 등기원인 권리자 및 기타사항
1 소유권보존 2020년 1월 1일 제1호 소유자 홍길동
【 을 구 】 (소유권 이외의 권리에 관한 사항)
순위번호 등기목적 접수 등기원인 권리자 및 기타사항
기록사항 없음
"""


class RegistryDocumentValidatorTest(unittest.TestCase):
    def test_accepts_valid_registry_with_empty_eul_records(self):
        result = validate_registry_document([VALID_REGISTRY_TEXT])

        self.assertTrue(result.accepted)
        self.assertEqual("집합건물", result.document_type)
        self.assertEqual((), result.missing_signals)

    def test_rejects_contract_disguised_with_registry_title_only(self):
        result = validate_registry_document([
            "등기사항전부증명서 부동산 전세계약서 임대인 임차인 보증금"
        ])

        self.assertEqual("INVALID_DOCUMENT", result.status)
        self.assertFalse(result.accepted)

    def test_marks_empty_text_layer_unreadable(self):
        result = validate_registry_document(["", "  "])

        self.assertEqual("UNREADABLE", result.status)
        self.assertEqual(("text_layer",), result.missing_signals)


if __name__ == "__main__":
    unittest.main()
