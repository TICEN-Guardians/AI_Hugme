"""
등기부등본 OCR 텍스트에서 위험진단에 필요한 구조화 데이터를 추출.

추출 범위:
- 갑구: 현재 소유자, 압류/가압류/가처분/경매개시/신탁 여부
- 을구: 근저당(채권최고액 포함), 전세권, 주택임차권(임차권등기)
"""
import re
from datetime import date

CAUSE_KEYWORDS = r"(?:매매|증여|상속|교환|신탁|경매|판결|공유물분할|현물출자|재산분할)"

_ENTRY_STOP = (
    r"(?:\d+(?:-\d+)?\s*(?:소유권보존|소유권이전|소유권말소|가압류|압류|근저당권설정|신탁|"
    r"경매개시결정|강제경매개시결정|등기명의인표시|전세권설정|주택임차권|가처분|공유자전원|민간임대주택)"
    r"|\d+-\d+\s*\d*번"
    r"|소유자|공유자|거래가액|【|-- ?이 ?하 ?여 ?백 ?--|관할등기소|\Z)"
)

OWNER_ENTRY_PATTERN = re.compile(
    r"소유자\s*([가-힣]{2,4})\s*(\d{6}-[\*0-9]+)\s*"
    r"(?:제\s*\d+\s*호\s*)?"
    r"(?:" + CAUSE_KEYWORDS + r")?\s*"
    r"(.+?)(?=" + _ENTRY_STOP + r")",
    re.DOTALL,
)

CO_OWNER_BLOCK_PATTERN = re.compile(
    r"공유자\s*(?:전원지분전부\s*이전)?\s*(?:제\s*\d+\s*호)?\s*(?:" + CAUSE_KEYWORDS + r")?\s*"
    r"(.+?)(?=" + _ENTRY_STOP + r")",
    re.DOTALL,
)
CO_OWNER_SUB_PATTERN = re.compile(
    r"지분\s*(\d+)\s*분의\s*(\d+)\s*([가-힣]{2,4})\s*(\d{6}-[\*0-9]+)\s*"
    r"(.+?)(?=지분|\Z)",
    re.DOTALL,
)

CANCELLATION_MENTION_PATTERN = re.compile(r"말소")

# ---------- 섹션 분리 ----------

_SECTION_GAP = re.compile(r"[【\[]\s*갑\s*구\s*[】\]]")
_SECTION_EUL = re.compile(r"[【\[]\s*을\s*구\s*[】\]]")
_NO_RECORDS = re.compile(r"기록\s*사항\s*없음")


def split_sections(text: str) -> dict:
    """전체 텍스트를 갑구/을구 텍스트로 분리. 못 찾으면 None (파싱 실패 신호)."""
    gap_m = _SECTION_GAP.search(text)
    eul_m = _SECTION_EUL.search(text)

    gap = None
    eul = None
    if gap_m:
        gap_end = eul_m.start() if eul_m else len(text)
        gap = text[gap_m.end():gap_end]
    if eul_m:
        eul = text[eul_m.end():]
    return {"gap": gap, "eul": eul}


# ---------- 권리 항목 파싱 (순위번호 단위) ----------

# 등기목적 분류
_PURPOSE_PRIORITY = [
    ("강제경매개시결정", "AUCTION"),
    ("임의경매개시결정", "AUCTION"),
    ("경매개시결정", "AUCTION"),
    ("가압류", "PROVISIONAL_SEIZURE"),
    ("압류", "SEIZURE"),
    ("가처분", "PROVISIONAL_DISPOSITION"),
    ("신탁", "TRUST"),
    ("가등기", "PROVISIONAL_REGISTRATION"),
    ("소유권보존", "OWNERSHIP"),
    ("소유권이전", "OWNERSHIP"),
    ("공유자전원", "OWNERSHIP"),
    ("근저당권설정", "MORTGAGE"),
    ("근저당권변경", "MORTGAGE_AMEND"),
    ("근저당권이전", "MORTGAGE_TRANSFER"),
    ("전세권설정", "JEONSE_RIGHT"),
    ("주택임차권", "LEASEHOLD_REGISTRATION"),
    ("민간임대주택", "OTHER"),
    ("등기명의인표시", "OTHER"),
]
_PURPOSE_ALT = "|".join(k for k, _ in _PURPOSE_PRIORITY)

_RIGHT_ENTRY_START = re.compile(
    r"(?<![\d\-])(\d{1,3}(?:-\d{1,3})?)\s*((?:\d{1,3}(?:-\d{1,3})?\s*번)|" + _PURPOSE_ALT + r")"
)

_KOREAN_DATE = re.compile(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일")
_AMOUNT = {
    "max_claim": re.compile(r"채권최고액\s*금\s*([\d,]+)\s*원"),
    "jeonse": re.compile(r"전세금\s*금\s*([\d,]+)\s*원"),
    "leasehold": re.compile(r"임차보증금\s*금\s*([\d,]+)\s*원"),
}
_AMOUNT["claim"] = re.compile(r"청구금액\s*금\s*([\d,]+)\s*원")
_RECEIPT_NO = re.compile(r"제\s*([\d]+)\s*호")
_HOLDER = re.compile(r"(?:근저당권자|전세권자|임차권자|채권자|권리자)\s*([가-힣A-Za-z0-9()\s]{2,30}?)(?=\s*\d{6}-|\s*\d{6}\s|\n|$)")
_CREDITOR = re.compile(r"근저당권자\s+([가-힣A-Za-z0-9()]+)")
_DEBTOR = re.compile(r"채무자\s+([가-힣]{2,10})")
_CANCEL_REFS = re.compile(r"(\d+(?:-\d+)?)\s*번")


def _to_iso(text: str) -> str | None:
    m = _KOREAN_DATE.search(text)
    if not m:
        return None
    y, mo, d = m.groups()
    return f"{y}-{int(mo):02d}-{int(d):02d}"


def _to_int(s: str) -> int | None:
    digits = re.sub(r"[^\d]", "", s)
    return int(digits) if digits else None


def _classify(head_collapsed: str, body_raw: str) -> tuple[str, list[str]]:
    """항목 텍스트로 (분류, 말소 참조 순위번호 리스트) 반환."""
    body_collapsed = re.sub(r"\s+", "", body_raw)
    if re.search(
        r"\d+(?:-\d+)?번.*?(?:등기)?말소",
        body_collapsed,
    ):
        refs = _CANCEL_REFS.findall(body_raw[:120])
        return "CANCELLATION", refs
    for keyword, kind in _PURPOSE_PRIORITY:
        if keyword in head_collapsed:
            return kind, []
    return "OTHER", []


def parse_section_entries(section_text: str, section_name: str) -> list[dict]:
    """섹션 텍스트를 순위번호 단위 항목 리스트로 분해하고 ACTIVE/CANCELLED 판정."""
    starts = list(_RIGHT_ENTRY_START.finditer(section_text))
    entries = []
    for i, m in enumerate(starts):
        rank = m.group(1)
        begin = m.start()
        end = starts[i + 1].start() if i + 1 < len(starts) else len(section_text)
        body = section_text[begin:end]
        head = re.sub(r"\s+", "", body[:80])  # 분류용: 공백 제거해 줄바꿈 깨짐 대응
        kind, cancel_refs = _classify(head, body)
        flat = re.sub(r"\s+", " ", body).strip()
        receipt_m = _RECEIPT_NO.search(body)
        holder_m = _HOLDER.search(flat)
        debtor_m = _DEBTOR.search(flat)
        amount = None
        for key in ("max_claim", "jeonse", "leasehold", "claim"):
            am = _AMOUNT[key].search(flat)
            if am:
                amount = _to_int(am.group(1))
                break
        entries.append({
            "section": section_name,
            "rank_no": rank,
            "kind": kind,
            "cancel_refs": cancel_refs,
            "receipt_no": receipt_m.group(1) if receipt_m else None,
            "registered_at": _to_iso(body),
            "holder": holder_m.group(1).strip() if holder_m else None,
            "debtor": debtor_m.group(1) if debtor_m else None,
            "amount": amount,
            "raw_text": flat,
            "status": "ACTIVE",
        })

    # 말소 항목이 참조하는 순위번호를 CANCELLED 처리
    cancelled_ranks = set()
    for e in entries:
        if e["kind"] == "CANCELLATION":
            cancelled_ranks.update(e["cancel_refs"])
    for e in entries:
        if e["rank_no"] in cancelled_ranks:
            e["status"] = "CANCELLED"

    return entries


def _apply_mortgage_amendments(entries: list[dict], mortgages: list[dict]) -> None:
    """'1-1 1번근저당권변경 ... 채권최고액 금X원' 같은 변경 부기를 원 근저당에 반영."""
    by_rank = {m["rank_no"]: m for m in mortgages}
    for e in entries:
        if e["kind"] != "MORTGAGE_AMEND":
            continue
        refs = _CANCEL_REFS.findall(e["raw_text"][:40])
        amount_m = _AMOUNT["max_claim"].search(e["raw_text"])
        if not refs or not amount_m:
            continue
        target = by_rank.get(refs[0])
        if target:
            target["max_claim_amount"] = _to_int(amount_m.group(1))


def extract_rights(text: str) -> dict:
    """
    갑구/을구 권리 정보 전체 추출.
    - EXTRACTED: 섹션 파싱 성공, 항목 있음
    - CONFIRMED_NONE: 섹션 파싱 성공, "기록사항 없음" 명시 or 해당 항목 0건
    - PARSE_FAILED: 섹션 자체를 못 찾음 -> 하위 플래그 UNKNOWN
    """
    sections = split_sections(text)

    result = {
        "gap_section_status": "PARSE_FAILED",
        "eul_section_status": "PARSE_FAILED",
        "rights": [],
        "mortgages": [],
        "jeonse_rights": [],
        "leasehold_registrations": [],
        "flags": {
            "seizure": "UNKNOWN",
            "provisional_seizure": "UNKNOWN",
            "provisional_disposition": "UNKNOWN",
            "auction_commenced": "UNKNOWN",
            "trust_registration": "UNKNOWN",
            "has_active_jeonse_right": "UNKNOWN",
            "has_leasehold_registration": "UNKNOWN",
        },
        "active_mortgage_count": None,
        "total_active_max_claim_amount": None,
    }

    # ----- 갑구 -----
    if sections["gap"] is not None:
        result["gap_section_status"] = "EXTRACTED"
        gap_entries = parse_section_entries(sections["gap"], "갑구")
        result["rights"].extend(gap_entries)

        flag_kinds = {
            "seizure": "SEIZURE",
            "provisional_seizure": "PROVISIONAL_SEIZURE",
            "provisional_disposition": "PROVISIONAL_DISPOSITION",
            "auction_commenced": "AUCTION",
            "trust_registration": "TRUST",
        }
        for flag, kind in flag_kinds.items():
            active = any(e["kind"] == kind and e["status"] == "ACTIVE" for e in gap_entries)
            result["flags"][flag] = "TRUE" if active else "FALSE"

    # ----- 을구 -----
    if sections["eul"] is not None:
        eul_text = sections["eul"]
        eul_entries = parse_section_entries(
            eul_text,
            "을구",
        )

        if (
            not eul_entries
            and _NO_RECORDS.search(eul_text[:500])
        ):
            result["eul_section_status"] = "CONFIRMED_NONE"
            result["flags"]["has_active_jeonse_right"] = "FALSE"
            result["flags"]["has_leasehold_registration"] = "FALSE"
            result["active_mortgage_count"] = 0
            result["total_active_max_claim_amount"] = 0
        elif eul_entries:
            result["eul_section_status"] = "EXTRACTED"
            result["rights"].extend(eul_entries)

            mortgages = []
            for e in eul_entries:
                if e["kind"] != "MORTGAGE" or "-" in e["rank_no"]:
                    continue
                amount_m = _AMOUNT["max_claim"].search(e["raw_text"])
                creditor_m = _CREDITOR.search(e["raw_text"])
                debtor_m = _DEBTOR.search(e["raw_text"])
                mortgages.append({
                    "rank_no": e["rank_no"],
                    "receipt_no": e["receipt_no"],
                    "registered_at": e["registered_at"],
                    "creditor": creditor_m.group(1) if creditor_m else None,
                    "debtor": debtor_m.group(1) if debtor_m else None,
                    "max_claim_amount": _to_int(amount_m.group(1)) if amount_m else None,
                    "status": e["status"],
                })
            _apply_mortgage_amendments(eul_entries, mortgages)
            result["mortgages"] = mortgages

            for e in eul_entries:
                if e["kind"] == "JEONSE_RIGHT":
                    amount_m = _AMOUNT["jeonse"].search(e["raw_text"])
                    result["jeonse_rights"].append({
                        "rank_no": e["rank_no"],
                        "receipt_no": e["receipt_no"],
                        "registered_at": e["registered_at"],
                        "holder": e["holder"],
                        "deposit_amount": _to_int(amount_m.group(1)) if amount_m else None,
                        "status": e["status"],
                    })
                elif e["kind"] == "LEASEHOLD_REGISTRATION":
                    amount_m = _AMOUNT["leasehold"].search(e["raw_text"])
                    result["leasehold_registrations"].append({
                        "rank_no": e["rank_no"],
                        "receipt_no": e["receipt_no"],
                        "registered_at": e["registered_at"],
                        "holder": e["holder"],
                        "deposit_amount": _to_int(amount_m.group(1)) if amount_m else None,
                        "status": e["status"],
                    })

            active_mortgages = [m for m in mortgages if m["status"] == "ACTIVE"]
            result["active_mortgage_count"] = len(active_mortgages)
            amounts = [m["max_claim_amount"] for m in active_mortgages]
            if any(a is None for a in amounts):
                # 유효 근저당인데 금액을 못 뽑은 게 있으면 합계를 확정하지 않음
                # (0으로 잘못 합산되는 것 방지 - 위험진단 팀 원칙)
                result["total_active_max_claim_amount"] = None
            else:
                result["total_active_max_claim_amount"] = sum(amounts)

            result["flags"]["has_active_jeonse_right"] = (
                "TRUE" if any(j["status"] == "ACTIVE" for j in result["jeonse_rights"]) else "FALSE"
            )
            result["flags"]["has_leasehold_registration"] = (
                "TRUE" if any(l["status"] == "ACTIVE" for l in result["leasehold_registrations"]) else "FALSE"
            )

    return result


# ---------- 문서 메타 ----------

_PROPERTY_ADDRESS = re.compile(r"\[(?:집합건물|건물|토지)\]\s*([^\n]+)")
_VIEWED_AT = re.compile(r"열람일시\s*[:：]\s*(\d{4})년\s*(\d{2})월\s*(\d{2})일")


def extract_document_meta(text: str) -> dict:
    addr_m = _PROPERTY_ADDRESS.search(text)
    viewed_m = _VIEWED_AT.search(text)
    issue_date = None
    if viewed_m:
        y, mo, d = viewed_m.groups()
        issue_date = f"{y}-{mo}-{d}"
    return {
        "property_address": addr_m.group(1).strip() if addr_m else None,
        "issue_date": issue_date,
    }


# ---------- 소유자 파싱 ----------

MAX_OWNER_ADDRESS_LENGTH = 255


def _clean_address(raw: str) -> str:
    """
    소유자 주소를 정규화한다.
    항목 종료 패턴을 못 만나면 캡처가 문서 뒷부분까지 번지므로,
    정상 주소로 볼 수 없는 길이는 잘라내지 않고 미확인으로 처리한다.
    """
    address = re.sub(r"\s+", " ", raw).strip().rstrip(",")

    if len(address) > MAX_OWNER_ADDRESS_LENGTH:
        return ""

    return address


def extract_owner_groups(text: str) -> list[list[dict]]:
    """
    갑구 텍스트에서 소유권 이전 이력을 '그룹' 단위로 반환.
    단독소유 항목은 원소 1개짜리 그룹, 공유자 항목은 여러 명이 든 그룹.
    마지막 그룹이 곧 현재 소유자(들)임.
    """
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
                "share": "1/1",
            }])
        else:
            block_text = m.group(1)
            people = []
            for sm in CO_OWNER_SUB_PATTERN.finditer(block_text):
                denom, numer, name, jumin_front, address = sm.groups()
                people.append({
                    "name": name,
                    "jumin_front": jumin_front,
                    "address": _clean_address(address),
                    "share": f"{numer}/{denom}",
                })
            if people:
                groups.append(people)
    return groups


def extract_owner_history(text: str) -> list[dict]:
    return [person for group in extract_owner_groups(text) for person in group]


def get_current_owners(text: str) -> list[dict]:
    groups = extract_owner_groups(text)
    return groups[-1] if groups else []


def has_cancellation_mention(text: str) -> bool:
    return bool(CANCELLATION_MENTION_PATTERN.search(text))


def calc_age_from_jumin(jumin_front: str, as_of: date | None = None) -> int | None:
    """
    마스킹된 주민번호 앞자리에서 만 나이를 역산.
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


def decide_parse_status(owners: list[dict], rights: dict) -> str:
    """
    문서 전체 파싱 상태 판정.
    FAILED       : 갑구/을구 둘 다 못 읽음
    PARTIAL      : 한쪽 섹션만 읽힘, 현재 소유자를 못 뽑음,
                   또는 소유자 주소를 확정하지 못함
    NEEDS_REVIEW : 섹션은 다 읽혔지만 유효 근저당 중 금액 미확인 건이 있어
                   채권최고액 합계를 확정할 수 없음
    SUCCESS      : 위 해당 없음
    """
    gap_ok = rights["gap_section_status"] == "EXTRACTED"
    eul_ok = rights["eul_section_status"] in ("EXTRACTED", "CONFIRMED_NONE")
    address_ok = all(owner.get("address") for owner in owners)

    if not gap_ok and not eul_ok:
        return "FAILED"
    if not gap_ok or not eul_ok or not owners or not address_ok:
        return "PARTIAL"
    if (rights["eul_section_status"] == "EXTRACTED"
            and rights["total_active_max_claim_amount"] is None):
        return "NEEDS_REVIEW"
    return "SUCCESS"



def extract_property_unit(text: str) -> dict:
    """집합건물 등기 표제부의 동·층·호·전유면적을 보수적으로 구조화한다."""
    collapsed = re.sub(r"\s+", " ", text)
    dong = re.search(r"(?:제\s*)?([가-힣A-Za-z0-9-]+)\s*동\b", collapsed)
    floor = re.search(r"(?:제\s*)?(-?\d+)\s*층\b", collapsed)
    ho = re.search(r"(?:제\s*)?([가-힣A-Za-z0-9-]+)\s*호\b", collapsed)
    exclusive_section = re.search(r"(?:전유부분의\s*건물의\s*표시|전유부분)(.{0,500})", collapsed)
    area_source = exclusive_section.group(1) if exclusive_section else collapsed
    area = re.search(r"(\d+(?:\.\d+)?)\s*(?:㎡|m2|m²)", area_source, re.IGNORECASE)
    return {
        "dong_name": dong.group(1) if dong else None,
        "floor": int(floor.group(1)) if floor else None,
        "ho_name": ho.group(1) if ho else None,
        "exclusive_area": float(area.group(1)) if area else None,
    }

def parse_register_fields(text: str) -> dict:
    history = extract_owner_history(text)
    current_owners = get_current_owners(text)

    owners = []
    for person in current_owners:
        owners.append({
            "name": person["name"],
            "jumin_front": person["jumin_front"],
            "address": person["address"],
            "share": person.get("share"),
            "status": "CURRENT",
            "age": calc_age_from_jumin(person["jumin_front"]),
        })

    meta = extract_document_meta(text)
    rights = extract_rights(text)
    unit = extract_property_unit(text)

    return {
        "current_owners": owners,
        "ownership_history": history,
        "has_cancellation_mention": has_cancellation_mention(text),
        "property_address": meta["property_address"],
        "issue_date": meta["issue_date"],
        **unit,
        "parse_status": decide_parse_status(owners, rights),
        "registry_rights": rights,
    }
