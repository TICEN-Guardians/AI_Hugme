"""
등기부등본 갑구(소유권에 관한 사항) OCR 텍스트에서 소유권 이력을 모두 추출하고,
그중 '현재 유효한 최종 소유자'를 판별.

핵심 포인트:
- 갑구에는 소유권보존/이전 이력이 순위번호 순으로 누적되어 쌓임 -> 첫 소유자가 아니라
  '말소되지 않은 마지막 항목'이 현재 소유자.
- 실제 등기부등본에는 취소선(말소) 처리된 등기가 있고, 보통 "OO번 소유권이전등기말소"
  형태로 별도 순위번호에 기록됨. OCR 텍스트만으로는 취소선 자체를 판별할 수 없으므로
  텍스트상의 "말소" 키워드 언급으로 근사 처리한다 (완벽하지 않음 - 아래 주석 참고).
"""
import re

from app.ocr.address_utils import extract_sigungu as _extract_sigungu

CAUSE_KEYWORDS = r"(?:매매|증여|상속|교환|신탁|경매|판결|공유물분할|현물출자|재산분할)"

# 다음 항목(순위번호+등기목적) 또는 다음 소유자, 거래가액, 문자열 끝에서 주소 캡처를 멈춤
_ENTRY_STOP = (
    r"(?:\d+\s*(?:소유권보존|소유권이전|소유권말소|가압류|압류|근저당권설정|신탁|경매개시결정)"
    r"|소유자|거래가액|\Z)"
)

OWNER_ENTRY_PATTERN = re.compile(
    r"소유자\s*([가-힣]{2,4})\s*(\d{6}-[\*0-9]+)\s*제\s*\d+\s*호\s*"
    r"(?:" + CAUSE_KEYWORDS + r")?\s*"
    r"(.+?)(?=" + _ENTRY_STOP + r")",
    re.DOTALL,
)

# "2번 소유권이전등기말소", "2번소유권말소" 등에서 말소 대상 순위번호를 잡기 위한 패턴.
# 주의: 지금은 순위번호를 개별 소유자 항목에 매핑하고 있지 않아서(원본 표 구조상
# 순위번호 컬럼을 별도로 파싱하지 않음), 이 패턴은 "몇 번째로 등장한 소유자 항목"인지와
# 직접 연결하지 못한다. 아래 extract_owner_history()는 우선 '말소'라는 단어가 아예
# 텍스트에 있는지 여부만 감지해 경고성 플래그로만 남기고, 자동 제외는 하지 않는다.
# -> 정확한 말소 처리를 하려면 순위번호 컬럼까지 구조적으로 파싱해야 함 (TODO).
CANCELLATION_MENTION_PATTERN = re.compile(r"말소")


def extract_owner_history(text: str) -> list[dict]:
    """텍스트에 등장하는 순서대로(=순위번호 순서) 소유자 이력을 모두 반환."""
    history = []
    for match in OWNER_ENTRY_PATTERN.finditer(text):
        name, jumin_front, address = match.groups()
        cleaned_address = re.sub(r"\s+", " ", address).strip().rstrip(",")
        history.append(
            {
                "name": name,
                "jumin_front": jumin_front,
                "address": cleaned_address,
            }
        )
    return history


def get_current_owner(text: str) -> dict | None:
    """
    소유권 이력 중 마지막 항목을 현재 소유자로 반환.
    이력이 없으면 None.
    """
    history = extract_owner_history(text)
    if not history:
        return None
    return history[-1]


def has_cancellation_mention(text: str) -> bool:
    """텍스트에 '말소' 언급이 있는지 여부 (있으면 사람이 원문 대조 확인 필요)."""
    return bool(CANCELLATION_MENTION_PATTERN.search(text))


def extract_sigungu(address: str) -> str | None:
    """호환용 재노출 - 실제 구현은 app.address_utils로 이동함. 새 코드는 그쪽을 직접 import."""
    return _extract_sigungu(address)


def parse_register_fields(text: str) -> dict:
    history = extract_owner_history(text)
    current = history[-1] if history else None

    return {
        "current_owner_name": current["name"] if current else None,
        "current_owner_address": current["address"] if current else None,
        "current_owner_address_sigungu": (
            extract_sigungu(current["address"]) if current else None
        ),
        "ownership_history": history,
        "has_cancellation_mention": has_cancellation_mention(text),
    }
