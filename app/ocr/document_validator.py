"""인터넷등기소 등기사항전부증명서 구조 검증.

텍스트 선택 가능한 PDF에서 추출한 페이지 텍스트를 대상으로 한다. 이 검증은
잘못된 문서·불완전한 PDF를 차단하기 위한 구조 검증이며 법적 진위 증명은 아니다.
"""

from dataclasses import dataclass
import re


_PROPERTY_TYPE = re.compile(r"\[(집합건물|건물|토지)\]")
_UNIQUE_NUMBER = re.compile(r"고유번호[:：]?[0-9]{4}-[0-9]{4}-[0-9]+")
_TITLE_MARKERS = ("등기사항전부증명서", "등기사항증명서")
_SECTION_MARKERS = {
    "title_section": ("【표제부】", "[표제부]"),
    "gap_section": ("【갑구】", "[갑구]"),
    "eul_section": ("【을구】", "[을구]"),
}
_TABLE_COLUMNS = ("순위번호", "등기목적", "접수", "등기원인", "권리자및기타사항")


@dataclass(frozen=True)
class RegistryDocumentValidation:
    status: str
    document_type: str | None
    signals: tuple[str, ...]
    missing_signals: tuple[str, ...]

    @property
    def accepted(self) -> bool:
        return self.status == "VALID_REGISTRY"


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def validate_registry_document(
    page_texts: list[str],
) -> RegistryDocumentValidation:
    """페이지 텍스트 전체에서 서로 독립적인 등기부 구조 신호를 확인한다."""
    readable_pages = [page for page in page_texts if page and page.strip()]
    if not readable_pages:
        return RegistryDocumentValidation(
            status="UNREADABLE",
            document_type=None,
            signals=(),
            missing_signals=("text_layer",),
        )

    compact = _compact("\n".join(readable_pages))
    signals: list[str] = ["text_layer"]

    if any(marker in compact for marker in _TITLE_MARKERS):
        signals.append("registry_title")

    property_match = _PROPERTY_TYPE.search(compact)
    document_type = property_match.group(1) if property_match else None
    if document_type:
        signals.append("property_type")

    if _UNIQUE_NUMBER.search(compact):
        signals.append("unique_number")

    for signal, markers in _SECTION_MARKERS.items():
        if any(marker in compact for marker in markers):
            signals.append(signal)

    if all(column in compact for column in _TABLE_COLUMNS):
        signals.append("registry_table_columns")

    required = (
        "registry_title",
        "property_type",
        "unique_number",
        "title_section",
        "gap_section",
        "eul_section",
        "registry_table_columns",
    )
    missing = tuple(signal for signal in required if signal not in signals)

    if not missing:
        status = "VALID_REGISTRY"
    elif len(signals) >= 5:
        status = "REVIEW_REQUIRED"
    else:
        status = "INVALID_DOCUMENT"

    return RegistryDocumentValidation(
        status=status,
        document_type=document_type,
        signals=tuple(signals),
        missing_signals=missing,
    )
