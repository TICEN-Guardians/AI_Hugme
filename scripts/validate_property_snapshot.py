from app.diagnosis.diagnosis_pipeline import DiagnosisPipeline
from app.diagnosis.external.address.schemas import ResolvedAddress
from app.diagnosis.external.building_ledger.quality import BuildingLedgerQuality
from app.diagnosis.external.building_ledger.schemas import BuildingLedgerKey
from app.diagnosis.external.building_ledger.service import BuildingLedgerResult
from app.diagnosis.external.building_ledger.unit_area import UnitAreaResult
from app.diagnosis.property_address_service import PropertyAddressResult
from app.diagnosis.property_snapshot import (
    build_property_snapshot,
    restore_property_address_result,
)
from app.diagnosis.schemas import (
    DiagnosisRequest,
    HousingType,
    PropertySnapshot,
)


LEDGER_KEY = BuildingLedgerKey(
    sigungu_code="11680",
    bjdong_code="10300",
    plat_code="0",
    bun="0185",
    ji="0000",
)


def resolved_result() -> PropertyAddressResult:
    return PropertyAddressResult(
        address=ResolvedAddress(
            road_address="서울특별시 강남구 개포로 516",
            jibun_address="서울특별시 강남구 개포동 185",
            legal_dong_code="1168010300",
            district="서울특별시 강남구 개포동",
            building_name="개포주공아파트",
            available_dongs=("101동", "102동"),
            building_ledger_key=LEDGER_KEY,
        ),
        building_ledger=BuildingLedgerResult(
            feature_values={
                "연면적(㎡)": 11667.18,
                "사용승인연도": 1991,
                "대지면적(㎡)": None,
            },
            selected_title={
                "bldNm": "개포주공아파트101동",
                "dongNm": "101",
                "etcPurps": "아파트",
                "mainPurpsCdNm": "공동주택",
                "hhldCnt": 327,
            },
            title_count=2,
            quality=BuildingLedgerQuality(
                blocking_errors=("LAND_AREA_MISSING",),
                warnings=("SEISMIC_DESIGN_UNKNOWN",),
            ),
        ),
        dong_name="101",
        ho_name="1301",
        housing_type=HousingType.APARTMENT,
        unit_area=UnitAreaResult(
            dong_name="101",
            ho_name="1301",
            floor=13,
            exclusive_area=84.52,
            common_area=32.1,
            total_area=116.62,
            row_count=3,
            zero_area_count=0,
        ),
    )


def diagnosis_request(**overrides) -> DiagnosisRequest:
    snapshot = build_property_snapshot(resolved_result())
    body = {
        "analysisId": 12,
        "address": "강남구 개포로 516",
        "dongName": "101",
        "hoName": "1301",
        "deposit": 500_000_000,
        "contractDate": "2026-09-01",
        "exclusiveArea": "84.52",
        "floor": 13,
        # SpringBoot 를 오가며 JSON 으로 한 번 변환되는 상황을 그대로 재현한다.
        "propertySnapshot": snapshot.model_dump(by_alias=True, mode="json"),
    }
    body.update(overrides)

    return DiagnosisRequest.model_validate(body)


class NeverCalledService:
    def resolve(self, **kwargs):
        raise AssertionError("스냅샷이 있으면 주소를 다시 조회하면 안 된다")


class RecordingService:
    def __init__(self) -> None:
        self.calls = 0

    def resolve(self, address, dong_name, ho_name):
        self.calls += 1
        return "재조회"


def pipeline(address_service) -> DiagnosisPipeline:
    return DiagnosisPipeline(
        property_address_service=address_service,
        property_matcher=None,
        market_feature_service=None,
        model_predictor=None,
    )


def main() -> None:
    original = resolved_result()
    snapshot = build_property_snapshot(original)
    wire = snapshot.model_dump(by_alias=True, mode="json")
    restored = restore_property_address_result(
        PropertySnapshot.model_validate(wire)
    )

    assert restored.address.road_address == original.address.road_address
    assert restored.address.district == original.address.district
    assert restored.address.building_name == original.address.building_name
    assert restored.address.building_ledger_key == LEDGER_KEY
    assert restored.housing_type == original.housing_type
    assert restored.dong_name == "101"
    assert restored.ho_name == "1301"
    assert (
        restored.building_ledger.feature_values
        == original.building_ledger.feature_values
    )
    assert (
        restored.building_ledger.selected_title["etcPurps"] == "아파트"
    )
    assert restored.building_ledger.quality.blocking_errors == (
        "LAND_AREA_MISSING",
    )
    assert restored.unit_area.exclusive_area == 84.52
    assert restored.unit_area.floor == 13

    # 스냅샷이 있으면 외부 조회를 하지 않는다.
    reused = pipeline(NeverCalledService())._resolve(diagnosis_request())
    assert reused.address.road_address == original.address.road_address

    # 동·호가 바뀌면 다른 집이므로 다시 조회한다.
    service = RecordingService()
    assert pipeline(service)._resolve(
        diagnosis_request(hoName="1302")
    ) == "재조회"
    assert service.calls == 1

    # 스냅샷 형식이 깨지면 다시 조회한다.
    service = RecordingService()
    broken = {**wire, "bun": "XXXX"}
    assert pipeline(service)._resolve(
        diagnosis_request(propertySnapshot=broken)
    ) == "재조회"
    assert service.calls == 1

    # 스냅샷이 아예 없으면(구버전 요청) 다시 조회한다.
    service = RecordingService()
    assert pipeline(service)._resolve(
        diagnosis_request(propertySnapshot=None)
    ) == "재조회"
    assert service.calls == 1

    # 단독·다가구는 층 없이도 요청이 성립한다.
    assert diagnosis_request(floor=None).floor is None

    print("매물 스냅샷 검증 완료")
    print("- 스냅샷 왕복 복원")
    print("- 스냅샷 재사용 시 외부 조회 없음")
    print("- 동·호 불일치 시 재조회")
    print("- 형식 오류 시 재조회")
    print("- 스냅샷 없을 때 재조회")
    print("- 층 없는 요청 허용")


if __name__ == "__main__":
    main()
