import re
from datetime import date


_SECTION_GAP = re.compile(r"[【\[]\s*갑\s*구\s*[】\]]")
_SECTION_EUL = re.compile(r"[【\[]\s*을\s*구\s*[】\]]")

_KIND_MARKERS = (
    ("강제경매개시결정", "AUCTION"),
    ("임의경매개시결정", "AUCTION"),
    ("경매개시결정", "AUCTION"),
    ("가압류", "PROVISIONAL_SEIZURE"),
    ("압류", "SEIZURE"),
    ("가처분", "PROVISIONAL_DISPOSITION"),
    ("근저당권변경", "MORTGAGE_AMEND"),
    ("근저당권이전", "MORTGAGE_TRANSFER"),
    ("근저당권설정", "MORTGAGE"),
    ("전세권설정", "JEONSE_RIGHT"),
    ("주택임차권", "LEASEHOLD_REGISTRATION"),
    ("가등기", "PROVISIONAL_REGISTRATION"),
    ("소유권보존", "OWNERSHIP"),
    ("소유권이전", "OWNERSHIP"),
    ("공유자전원", "OWNERSHIP"),
    ("신탁", "TRUST"),
)


def split_registry_sections(text: str) -> dict[str, str | None]:
    gap_match = _SECTION_GAP.search(text)
    eul_match = _SECTION_EUL.search(text)
    gap = None
    eul = None
    if gap_match:
        gap_end = eul_match.start() if eul_match else len(text)
        gap = text[gap_match.end():gap_end]
    if eul_match:
        eul = text[eul_match.end():]
    return {"gap": gap, "eul": eul}


def classify_right_kind(evidence: str) -> str:
    compact = re.sub(r"\s+", "", evidence or "")
    if "말소" in compact:
        return "CANCELLATION"
    if "근저당권" in compact and "변경" in compact:
        return "MORTGAGE_AMEND"
    if "근저당권" in compact and "이전" in compact:
        return "MORTGAGE_TRANSFER"
    for marker, kind in _KIND_MARKERS:
        if marker in compact:
            return kind
    return "OTHER"


def target_rank_nos_from_purpose(purpose: str) -> list[str]:
    ranks = []
    for match in re.finditer(r"(\d+(?:-\d+)?)\s*번(?:\s*\((\d+)\))?", purpose or ""):
        base, suffix = match.groups()
        rank = f"{base}({suffix})" if suffix else base
        if rank not in ranks:
            ranks.append(rank)
    return ranks


def calc_age_from_jumin(jumin_front: str, as_of: date | None = None) -> int | None:
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
