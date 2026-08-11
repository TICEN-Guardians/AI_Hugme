"""
주소 문자열에서 '시/도 + 시/군/구'만 뽑아 정규화하는 공용 함수.
"""
import re

_SIDO_MAP = {
    "서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구",
    "인천광역시": "인천", "광주광역시": "광주", "대전광역시": "대전",
    "울산광역시": "울산", "세종특별자치시": "세종", "경기도": "경기",
    "강원특별자치도": "강원", "강원도": "강원", "충청북도": "충북",
    "충청남도": "충남", "전북특별자치도": "전북", "전라북도": "전북",
    "전라남도": "전남", "경상북도": "경북", "경상남도": "경남",
    "제주특별자치도": "제주",
}

_SIGUNGU_PATTERN = re.compile(
    r"([가-힣]+(?:특별시|광역시|특별자치시|특별자치도|도))\s*([가-힣]+[시군구])"
)
_SIGUNGU_SHORT_PATTERN = re.compile(r"([가-힣]{2})\s+([가-힣]+[시군구])")


def extract_sigungu(address: str | None) -> str | None:
    """
    예) "부산광역시 해운대구 반여동 1034-4번지" -> "부산 해운대구"
        "대전 동구 동서대로1683번길 19"       -> "대전 동구"
    """
    if not address:
        return None

    match = _SIGUNGU_PATTERN.search(address)
    if match:
        sido_full, gungu = match.groups()
        sido_short = _SIDO_MAP.get(sido_full, sido_full[:2])
        return f"{sido_short} {gungu}"

    match = _SIGUNGU_SHORT_PATTERN.search(address)
    if match:
        sido_short, gungu = match.groups()
        return f"{sido_short} {gungu}"

    return None
