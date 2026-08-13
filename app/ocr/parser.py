"""
등기부등본 갑구(소유권에 관한 사항) OCR 텍스트에서 소유권 이력을 모두 추출하고,
그중 '현재 유효한 최종 소유자'를 판별.
"""
import re
from datetime import date

CAUSE_KEYWORDS = r"(?:매매|증여|상속|교환|신탁|경매|판결|공유물분할|현물출자|재산분할)"

# 다음 항목들 끝에서 캡처를 멈춤
_ENTRY_STOP = (
    r"(?:\d+(?:-\d+)?\s*(?:소유권보존|소유권이전|소유권말소|가압류|압류|근저당권설정|신탁|"
    r"경매개시결정|강제경매개시결정|등기명의인표시|전세권설정|주택임차권|가처분)"
    r"|\d+-\d+\s*\d*번"
    r"|소유자|공유자|거래가액|【|-- ?이 ?하 ?여 ?백 ?--|관할등기소|\Z)"
)

OWNER_ENTRY_PATTERN = re.compile(
    r"소유자\s*([가-힣]{2,4})\s*(\d{6}-[\*0-9]+)\s*제\s*\d+\s*호\s*"
    r"(?:" + CAUSE_KEYWORDS + r")?\s*"
    r"(.+?)(?=" + _ENTRY_STOP + r")",
    re.DOTALL,
)

CO_OWNER_BLOCK_PATTERN = re.compile(
    r"공유자\s*(?:제\s*\d+\s*호)?\s*(?:" + CAUSE_KEYWORDS + r")?\s*"
    r"(.+?)(?=" + _ENTRY_STOP + r")",
    re.DOTALL,
)

CO_OWNER_SUB_PATTERN = re.compile(
    r"지분\s*\d+\s*분의\s*\d+\s*([가-힣]{2,4})\s*(\d{6}-[\*0-9]+)\s*"
    r"(.+?)(?=지분|\Z)",
    re.DOTALL,
)

CANCELLATION_MENTION_PATTERN = re.compile(r"말소")

def _clean_address(raw: str) -> str:
    return re.sub(r"\s+", " ", raw).strip().rstrip(",")

def extract_owner_groups(text: str) -> list[list[dict]]:
    matches = []
    for m in OWNER_ENTRY_PATTERN.finditer(text):
        matches.append((m.start(), "single", m))
    for m in CO_OWNER_BLOCK_PATTERN.finditer(text):
        matches.append((m.start(), "co", m))
    matches.sort(key=lambda x: x[0])
 
    groups: list[list[dict]] = []
    for _, kind, m in matches:
        if kind == "single":
            name, jumin_front, address = m.groups()
            groups.append([{
                "name": name,
                "jumin_front": jumin_front,
                "address": _clean_address(address),
            }])
        else:
            block_text = m.group(1)
            people = []
            for sm in CO_OWNER_SUB_PATTERN.finditer(block_text):
                name, jumin_front, address = sm.groups()
                people.append({
                    "name": name,
                    "jumin_front": jumin_front,
                    "address": _clean_address(address),
                })
            if people:
                groups.append(people)
    return groups

def extract_owner_history(text: str) -> list[dict]:
    """이력 전체를 반환 - 화면 표시/이력 확인용."""
    return [person for group in extract_owner_groups(text) for person in group]


def get_current_owners(text: str) -> list[dict]:
    """
    소유권 이력 중 마지막 그룹을 현재 소유자로 반환.
    """
    groups = extract_owner_groups(text)
    return groups[-1] if groups else []


def has_cancellation_mention(text: str) -> bool:
    """텍스트에 '말소' 언급이 있는지 여부 (있으면 사람이 원문 대조 확인 필요)."""
    return bool(CANCELLATION_MENTION_PATTERN.search(text))

def calc_age_from_jumin(jumin_front: str, as_of: date | None = None) -> int | None:
    """
    마스킹된 주민번호 앞자리("YYMMDD-*******")에서 만 나이를 역산.
    
    """
    as_of = as_of or date.today()
    digits = jumin_front.split("-")[0]
    if len(digits) != 6 or not digits.isdigit():
        return None
 
    yy, mm, dd = int(digits[:2]), int(digits[2:4]), int(digits[4:6])
    age_if_1900 = as_of.year - (1900 + yy)
    year = (1900 + yy) if age_if_1900 <= 100 else (2000 + yy)
 
    try:
        birth = date(year, mm, dd)
    except ValueError:
        return None
 
    return as_of.year - birth.year - ((as_of.month, as_of.day) < (birth.month, birth.day))

def parse_register_fields(text: str) -> dict:
    history = extract_owner_history(text)
    current_owners = get_current_owners(text)

    owners = []
    for person in current_owners:
        owners.append({
            "name": person["name"],
            "jumin_front": person["jumin_front"],
            "address": person["address"],
            "age": calc_age_from_jumin(person["jumin_front"]),
        })
 
    return {
        "current_owners": owners,
        "ownership_history": history,
        "has_cancellation_mention": has_cancellation_mention(text),
    }
