from enum import StrEnum


class FeatureSource(StrEnum):
    USER_INPUT = "user_input"
    ADDRESS = "address"
    PROPERTY_RESOLVER = "property_resolver"
    PROPERTY_DETAIL = "property_detail"
    PROPERTY_MATCH = "property_match"
    BUILDING_LEDGER = "building_ledger"
    RONE = "rone"
    COFIX = "cofix"
    ECOS = "ecos"
    KOSIS = "kosis"
    DERIVED = "derived"
    UNRESOLVED = "unresolved"


PROPERTY_DETAIL_FEATURES = {
    "전용면적(㎡)",
    "계약면적(㎡)",
    "대지권면적(㎡)",
    "층",
}

BUILDING_LEDGER_FEATURES = {
    "연면적(㎡)",
    "대지면적(㎡)",
}

PROPERTY_MATCH_FEATURES = {
    "단지명",
    "건물명",
}

DERIVED_FEATURES = {
    "최종건축연령",
    "거래시점건축연령_파생",
    "대지대비연면적비율_파생",
    "계약월",
    "계약월_파생",
}

# 파이프라인에 아직 데이터 원천이 연결되지 않아 항상 기본값으로 채워지는 Feature.
#
# 이런 Feature까지 fallback 으로 세면 해당 모델을 쓰는 진단은 시세 신뢰도가 항상
# LOW 로 나와 "이번 건이 유난히 부실한가"를 구분할 수 없게 된다.
# 그래서 fallback 집계에서 빼고 아래 경고 코드로만 알린다.
#
# 대지권면적(㎡)  : 매매_연립다세대 전용. 건축물대장 표제부에도 없고 등기부 파서도
#                   아직 (대지권의 표시)를 읽지 않는다. 원천이 생기면 이 목록에서 뺀다.
UNAVAILABLE_FEATURES = {
    "대지권면적(㎡)",
}

UNAVAILABLE_FEATURE_WARNINGS = {
    "대지권면적(㎡)": "LAND_RIGHT_AREA_UNAVAILABLE",
}


def get_feature_source(
    feature_name: str,
) -> FeatureSource:
    if feature_name == "시군구":
        return FeatureSource.ADDRESS

    if feature_name == "주택유형":
        return FeatureSource.PROPERTY_RESOLVER

    if feature_name in PROPERTY_DETAIL_FEATURES:
        return FeatureSource.PROPERTY_DETAIL

    if feature_name in PROPERTY_MATCH_FEATURES:
        return FeatureSource.PROPERTY_MATCH

    if (
        feature_name in BUILDING_LEDGER_FEATURES
        or feature_name.startswith("건축물대장_")
    ):
        return FeatureSource.BUILDING_LEDGER

    if feature_name.startswith("RONE_"):
        return FeatureSource.RONE

    if feature_name == "신규취급액기준_COFIX":
        return FeatureSource.COFIX

    if feature_name.startswith("ECOS_"):
        return FeatureSource.ECOS

    if feature_name.startswith("KOSIS_"):
        return FeatureSource.KOSIS

    if feature_name in DERIVED_FEATURES:
        return FeatureSource.DERIVED

    return FeatureSource.UNRESOLVED