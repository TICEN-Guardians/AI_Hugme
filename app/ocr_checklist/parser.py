"""주택임대차계약서 OCR 결과 파싱."""

import re


COMPANY_KEYWORDS = (
    "주식회사",
    "유한회사",
    "합자회사",
    "합명회사",
    "법인등록번호",
    "(주)",
    "㈜",
)

CHECKED_MARKS = "■☑✓✔●"


def clean_value(value: str | None) -> str | None:
    """OCR 결과의 불필요한 공백과 구분자를 정리한다."""
    if not value:
        return None

    value = re.sub(r"\s+", " ", value)
    value = value.strip(" :：,.-")

    return value or None


def extract_housing_type(text: str) -> str | None:
    """1페이지 건물의 구조·용도 입력값을 추출한다."""
    patterns = [
        (
            r"건\s*물\s*구조\s*[·‧ㆍ.]?\s*용도\s*"
            r"(.+?)(?=면\s*적|임차할\s*부분)"
        ),
        (
            r"구조\s*[·‧ㆍ.]?\s*용도\s*[:：]?\s*"
            r"(.+?)(?=\n|면\s*적)"
        ),
        (
            r"건\s*물\s*(?:구조\s*[·‧ㆍ.]?\s*용도)?\s*[:：]?\s*"
            r"(.+?)(?=면\s*적|임대할\s*부분|임차할\s*부분)"
        ),
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)

        if match:
            return clean_value(match.group(1))

    return None


def normalize_housing_type(
    raw_value: str | None,
) -> tuple[str | None, str | None]:
    """계약서 구조·용도를 Spring 주택 유형으로 변환한다."""
    if not raw_value:
        return None, None

    normalized = re.sub(r"\s+", "", raw_value)

    if "아파트" in normalized:
        return "APARTMENT", "아파트"

    if "오피스텔" in normalized or "업무시설" in normalized:
        return "OFFICETEL", "오피스텔"

    if any(
        keyword in normalized
        for keyword in ("빌라", "다세대주택", "연립주택")
    ):
        return "VILLA", "빌라"

    if any(
        keyword in normalized
        for keyword in ("단독주택", "다가구주택")
    ):
        return "HOUSE", "주택"

    return None, None


def extract_location(text: str) -> str | None:
    """1페이지 소재지의 도로명주소를 추출한다."""
    patterns = [
        (
            r"소\s*재\s*지\s*"
            r"(?:\(\s*도로명주소\s*\))?\s*[:：]?\s*"
            r"(.+?)(?=토\s*지|지\s*목|건\s*물)"
        ),
        r"소재지\s*[:：]\s*(.+?)(?=\n)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)

        if match:
            value = clean_value(match.group(1))

            if value and value != "도로명주소":
                return value

    return None


def extract_detail_address(text: str) -> str | None:
    """1페이지 임차할 부분의 동·층·호를 추출한다."""
    patterns = [
        (
            r"임차할\s*부분\s*"
            r"(?:상세주소가\s*있는\s*경우\s*동\s*[·‧ㆍ.]?\s*층\s*"
            r"[·‧ㆍ.]?\s*호\s*정확히\s*기재)?\s*"
            r"(.+?)(?=면\s*적|계약의\s*종류)"
        ),
        r"임차할\s*부분\s*[:：]?\s*(.+?)(?=\n)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)

        if match:
            value = clean_value(match.group(1))

            if value and "상세주소가 있는 경우" not in value:
                return value

    return None


def combine_contract_address(
    location: str | None,
    detail: str | None,
) -> str | None:
    """소재지와 상세주소를 하나의 계약주소로 합친다."""
    location = clean_value(location)
    detail = clean_value(detail)

    if location and detail:
        # 상세주소가 이미 소재지에 포함된 경우 중복해서 붙이지 않는다.
        if detail in location:
            return location

        return f"{location} {detail}"

    if location:
        return location

    if detail:
        return detail

    return None


def detect_contract_type(text: str) -> str | None:
    """체크된 신규·갱신 계약 유형을 판별한다."""
    mark = re.escape(CHECKED_MARKS)

    new_pattern = rf"[{mark}]\s*신규\s*계약"
    renewal_patterns = [
        rf"[{mark}]\s*합의에\s*의한\s*재계약",
        rf"[{mark}].{{0,30}}계약갱신요구권",
        rf"[{mark}].{{0,30}}갱신계약",
    ]

    if re.search(new_pattern, text, re.DOTALL):
        return "NEW"

    if any(
        re.search(pattern, text, re.DOTALL)
        for pattern in renewal_patterns
    ):
        return "RENEWAL"

    # 구형 부동산임대차계약서는 신규/갱신 체크란이 없는 경우가 많다.
    # 재계약·갱신 문구가 없다면 새로 작성된 계약으로 정규화한다.
    if (
        "부동산임대차계약서" in re.sub(r"\s+", "", text)
        and not re.search(r"재\s*계약|갱\s*신", text)
    ):
        return "NEW"

    return None


def detect_party_type(party_text: str | None) -> str:
    """회사 관련 표시가 있으면 COMPANY, 아니면 PERSON."""
    if not party_text:
        return "PERSON"

    normalized = re.sub(r"\s+", "", party_text)

    if any(
        re.sub(r"\s+", "", keyword) in normalized
        for keyword in COMPANY_KEYWORDS
    ):
        return "COMPANY"

    return "PERSON"


def extract_landlord_section(text: str) -> str | None:
    """서명란의 임대인 부분을 추출한다."""
    signature_start = text.rfind("본 계약을 증명")

    if signature_start >= 0:
        text = text[signature_start:]

    match = re.search(
        r"임\s*대\s*인\s*(.+?)(?=임\s*차\s*인)",
        text,
        re.DOTALL,
    )

    return clean_value(match.group(1)) if match else None


def extract_tenant_section(text: str) -> str | None:
    """서명란의 임차인 부분을 추출한다."""
    signature_start = text.rfind("본 계약을 증명")

    if signature_start >= 0:
        text = text[signature_start:]

    match = re.search(
        r"임\s*차\s*인\s*(.+?)(?=개\s*업\s*공인중개사|\Z)",
        text,
        re.DOTALL,
    )

    return clean_value(match.group(1)) if match else None


def detect_fixed_date(text: str) -> bool | None:
    """확정일자 부여란에 날짜가 작성됐는지 확인한다."""
    match = re.search(
        r"확정일자\s*부여란\s*(.+?)(?=\[\s*계약내용\s*\]|제1조)",
        text,
        re.DOTALL,
    )

    if not match:
        return False

    region = match.group(1)

    date_patterns = [
        r"\d{4}\s*[년./-]\s*\d{1,2}\s*[월./-]\s*\d{1,2}",
        r"\d{2}\s*[./-]\s*\d{1,2}\s*[./-]\s*\d{1,2}",
    ]

    if any(re.search(pattern, region) for pattern in date_patterns):
        return True

    return False


def detect_officetel_residential(
    housing_type_code: str | None,
    housing_raw: str | None,
) -> bool | None:
    """오피스텔의 주거용 표시 여부를 확인한다."""
    if housing_type_code != "OFFICETEL":
        return False

    if not housing_raw:
        return None

    normalized = re.sub(r"\s+", "", housing_raw)

    if any(
        keyword in normalized
        for keyword in ("주거용", "주택용도", "주거목적")
    ):
        return True

    return False


def detect_landlord_proxy(text: str) -> bool | None:
    """임대인 대리인란에 실제 값이 작성됐는지 확인한다."""
    landlord_section = extract_landlord_section(text)

    if not landlord_section:
        return False

    match = re.search(
        r"대\s*리\s*인\s*(.+?)(?=임\s*차\s*인|\Z)",
        landlord_section,
        re.DOTALL,
    )

    if not match:
        return False

    proxy_value = re.sub(
        r"(주소|주민등록번호|성명|전화|서명|날인|\s|[:：])",
        "",
        match.group(1),
    )

    return bool(proxy_value)


def parse_checklist_fields(text: str) -> dict:
    """OCR 전체 텍스트를 Spring 체크리스트 응답으로 변환한다."""
    housing_raw = extract_housing_type(text)
    housing_code, housing_name = normalize_housing_type(housing_raw)

    location = extract_location(text)
    detail_address = extract_detail_address(text)

    landlord_section = extract_landlord_section(text)
    tenant_section = extract_tenant_section(text)

    return {
        "housingTypeCode": housing_code,
        "housingTypeName": housing_name,
        "contractAddress": combine_contract_address(
            location,
            detail_address,
        ),
        "contractType": detect_contract_type(text),
        "tenantType": detect_party_type(tenant_section),
        "landlordType": detect_party_type(landlord_section),
        "fixedDateConfirmed": detect_fixed_date(text),
        "officetelResidentialMarked": detect_officetel_residential(
            housing_code,
            housing_raw,
        ),
        "landlordProxyContract": detect_landlord_proxy(text),
    }

REQUIRED_FIELDS = (
    "housingTypeCode",
    "contractAddress",
    "contractType",
    "fixedDateConfirmed",
    "officetelResidentialMarked",
    "landlordProxyContract",
)


def find_missing_fields(fields: dict) -> list[str]:
    return [
        field
        for field in REQUIRED_FIELDS
        if fields.get(field) is None
    ]

HOUSING_TYPE_NAMES = {
    "APARTMENT": "아파트",
    "OFFICETEL": "오피스텔",
    "VILLA": "빌라",
    "HOUSE": "주택",
}


def apply_defaults(fields: dict) -> dict:
    result = fields.copy()

    housing_code = result.get("housingTypeCode")
    result["housingTypeName"] = HOUSING_TYPE_NAMES.get(
        housing_code
    )

    if result.get("tenantType") is None:
        result["tenantType"] = "PERSON"

    if result.get("landlordType") is None:
        result["landlordType"] = "PERSON"

    return result
