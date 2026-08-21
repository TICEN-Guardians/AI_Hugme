"""텍스트 선택 가능한 인터넷등기소 PDF 로더."""

from dataclasses import dataclass

import fitz

from app.ocr.document_validator import (
    RegistryDocumentValidation,
    validate_registry_document,
)


MAX_REGISTRY_PDF_BYTES = 25 * 1024 * 1024
MAX_REGISTRY_PAGES = 100


class RegistryPdfError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class RegistryPdfDocument:
    page_texts: tuple[str, ...]
    text: str
    validation: RegistryDocumentValidation


def load_registry_pdf(pdf_bytes: bytes) -> RegistryPdfDocument:
    if not pdf_bytes:
        raise RegistryPdfError("EMPTY_FILE", "빈 파일입니다.")
    if len(pdf_bytes) > MAX_REGISTRY_PDF_BYTES:
        raise RegistryPdfError(
            "FILE_TOO_LARGE",
            "등기부등본 PDF는 25MB 이하여야 합니다.",
        )
    if not pdf_bytes.startswith(b"%PDF-"):
        raise RegistryPdfError(
            "NOT_PDF",
            "PDF 형식의 파일이 아닙니다.",
        )

    try:
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        raise RegistryPdfError(
            "BROKEN_PDF",
            "PDF 파일을 열 수 없습니다.",
        ) from exc

    try:
        if document.needs_pass:
            raise RegistryPdfError(
                "PASSWORD_PROTECTED",
                "암호가 설정된 PDF는 분석할 수 없습니다.",
            )
        if document.page_count < 1 or document.page_count > MAX_REGISTRY_PAGES:
            raise RegistryPdfError(
                "INVALID_PAGE_COUNT",
                f"등기부등본 PDF는 1~{MAX_REGISTRY_PAGES}쪽이어야 합니다.",
            )
        page_texts = tuple(page.get_text() for page in document)
    finally:
        document.close()

    validation = validate_registry_document(list(page_texts))
    if validation.status == "UNREADABLE":
        raise RegistryPdfError(
            "TEXT_LAYER_REQUIRED",
            "텍스트 선택이 가능한 인터넷등기소 발급 PDF를 업로드해 주세요.",
        )
    if validation.status == "INVALID_DOCUMENT":
        raise RegistryPdfError(
            "INVALID_DOCUMENT",
            "등기사항전부증명서로 확인되지 않습니다. 인터넷등기소 발급 PDF를 업로드해 주세요.",
        )
    if validation.status == "REVIEW_REQUIRED":
        raise RegistryPdfError(
            "REVIEW_REQUIRED",
            "등기부 구조 일부를 확인하지 못했습니다. 완전한 발급 PDF를 다시 업로드해 주세요.",
        )

    return RegistryPdfDocument(
        page_texts=page_texts,
        text="\n".join(page_texts).strip(),
        validation=validation,
    )
