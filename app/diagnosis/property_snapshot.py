"""properties/resolve 결과를 스냅샷으로 담고 다시 꺼내는 변환기.

resolve 와 analyze 가 같은 주소를 두 번 조회하던 것을 없애기 위해 쓴다.
resolve 응답에 스냅샷을 실어 보내고, analyze 요청이 그대로 돌려주면 재사용한다.

복원은 항상 실패할 수 있다고 보고 호출부에서 예외를 잡아 재조회로 되돌린다.
"""
from app.diagnosis.external.address.schemas import ResolvedAddress
from app.diagnosis.external.building_ledger.quality import BuildingLedgerQuality
from app.diagnosis.external.building_ledger.schemas import BuildingLedgerKey
from app.diagnosis.external.building_ledger.service import BuildingLedgerResult
from app.diagnosis.external.building_ledger.unit_area import UnitAreaResult
from app.diagnosis.property_address_service import PropertyAddressResult
from app.diagnosis.schemas import PropertySnapshot, UnitAreaSnapshot


class PropertySnapshotError(ValueError):
    pass


# 주택유형 세부 판정(단독·다가구 매매)과 단지명 매칭에만 쓰는 표제부 필드.
# 표제부 전체를 담으면 스냅샷이 불필요하게 커진다.
TITLE_KEYS = ("bldNm", "dongNm", "etcPurps", "mainPurpsCdNm")


def build_property_snapshot(
    result: PropertyAddressResult,
) -> PropertySnapshot:
    address = result.address
    key = address.building_ledger_key
    ledger = result.building_ledger

    return PropertySnapshot(
        roadAddress=address.road_address,
        jibunAddress=address.jibun_address,
        legalDongCode=address.legal_dong_code,
        district=address.district,
        buildingName=address.building_name,
        sigunguCode=key.sigungu_code,
        bjdongCode=key.bjdong_code,
        platCode=key.plat_code,
        bun=key.bun,
        ji=key.ji,
        housingType=result.housing_type,
        dongName=result.dong_name,
        hoName=result.ho_name,
        ledgerFeatureValues=dict(ledger.feature_values),
        ledgerTitle={
            name: str(ledger.selected_title.get(name))
            for name in TITLE_KEYS
            if ledger.selected_title.get(name) is not None
        },
        ledgerTitleCount=ledger.title_count,
        qualityBlocking=list(ledger.quality.blocking_errors),
        qualityWarnings=list(ledger.quality.warnings),
        unitArea=_unit_area_snapshot(result.unit_area),
    )


def restore_property_address_result(
    snapshot: PropertySnapshot,
) -> PropertyAddressResult:
    try:
        key = BuildingLedgerKey(
            sigungu_code=snapshot.sigungu_code,
            bjdong_code=snapshot.bjdong_code,
            plat_code=snapshot.plat_code,
            bun=snapshot.bun,
            ji=snapshot.ji,
        )
    except ValueError as exc:
        raise PropertySnapshotError(
            "스냅샷 건축물대장 키 형식 오류"
        ) from exc

    if not snapshot.road_address or not snapshot.district:
        raise PropertySnapshotError("스냅샷 주소 값 누락")

    if not snapshot.ledger_feature_values:
        raise PropertySnapshotError("스냅샷 건축물대장 Feature 누락")

    address = ResolvedAddress(
        road_address=snapshot.road_address,
        jibun_address=snapshot.jibun_address,
        legal_dong_code=snapshot.legal_dong_code,
        district=snapshot.district,
        building_name=snapshot.building_name,
        # 동 후보 목록은 후보 선택이 끝난 뒤에는 쓰이지 않는다.
        available_dongs=(),
        building_ledger_key=key,
    )
    building_ledger = BuildingLedgerResult(
        feature_values=dict(snapshot.ledger_feature_values),
        selected_title=dict(snapshot.ledger_title),
        title_count=snapshot.ledger_title_count,
        quality=BuildingLedgerQuality(
            blocking_errors=tuple(snapshot.quality_blocking),
            warnings=tuple(snapshot.quality_warnings),
        ),
    )

    return PropertyAddressResult(
        address=address,
        building_ledger=building_ledger,
        dong_name=snapshot.dong_name,
        ho_name=snapshot.ho_name,
        housing_type=snapshot.housing_type,
        unit_area=_restore_unit_area(snapshot.unit_area),
    )


def matches_request(
    snapshot: PropertySnapshot,
    address: str,
    dong_name: str | None,
    ho_name: str | None,
) -> bool:
    """스냅샷이 이번 요청과 같은 대상인지 확인한다.

    사용자가 동·호를 바꾼 뒤 옛 스냅샷을 보내면 다른 집으로 진단하게 되므로 막는다.
    주소는 표기가 달라질 수 있어(사용자 입력 vs 도로명주소) 비교 대상에서 뺀다.
    """
    return (
        _blank_to_none(snapshot.dong_name) == _blank_to_none(dong_name)
        and _blank_to_none(snapshot.ho_name) == _blank_to_none(ho_name)
        and bool(str(address or "").strip())
    )


def _unit_area_snapshot(
    unit_area: UnitAreaResult | None,
) -> UnitAreaSnapshot | None:
    if unit_area is None:
        return None

    return UnitAreaSnapshot(
        dongName=unit_area.dong_name,
        hoName=unit_area.ho_name,
        floor=unit_area.floor,
        exclusiveArea=unit_area.exclusive_area,
        commonArea=unit_area.common_area,
        totalArea=unit_area.total_area,
    )


def _restore_unit_area(
    snapshot: UnitAreaSnapshot | None,
) -> UnitAreaResult | None:
    if snapshot is None:
        return None

    if snapshot.exclusive_area <= 0:
        raise PropertySnapshotError("스냅샷 전유면적 오류")

    return UnitAreaResult(
        dong_name=snapshot.dong_name,
        ho_name=snapshot.ho_name,
        floor=snapshot.floor,
        exclusive_area=snapshot.exclusive_area,
        common_area=snapshot.common_area,
        total_area=snapshot.total_area,
        # 원본 행 수는 면적 합산에만 쓰였고 추론에는 쓰이지 않는다.
        row_count=0,
        zero_area_count=0,
    )


def _blank_to_none(value: str | None) -> str | None:
    text = str(value or "").strip()
    return text or None
