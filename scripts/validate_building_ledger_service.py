from app.diagnosis.external.building_ledger.schemas import (
    BuildingLedgerKey,
)
from app.diagnosis.external.building_ledger.service import (
    BuildingLedgerService,
)


class FakeClient:
    def get_title(
        self,
        key: BuildingLedgerKey,
    ) -> list[dict]:
        assert key.sigungu_code == "11680"

        return [
            {
                "mainAtchGbCdNm": "주건축물",
                "dongNm": "301",
                "bldNm": "대청아파트301동",
                "totArea": "8778.66",
                "hhldCnt": "161",
            },
            {
                "mainAtchGbCdNm": "주건축물",
                "dongNm": "101",
                "bldNm": "대치아파트101동",
                "totArea": "11667.18",
                "platArea": "0",
                "grndFlrCnt": "15",
                "ugrndFlrCnt": "1",
                "hhldCnt": "327",
                "rideUseElvtCnt": "0",
                "emgenUseElvtCnt": "0",
                "strctCdNm": "철근콘크리트구조",
                "mainPurpsCdNm": "공동주택",
                "rserthqkDsgnApplyYn": "1",
                "useAprDay": "19911120",
            },
        ]


def main() -> None:
    key = BuildingLedgerKey(
        sigungu_code="11680",
        bjdong_code="10300",
        plat_code="0",
        bun="0012",
        ji="0000",
    )

    service = BuildingLedgerService(
        client=FakeClient(),
    )

    result = service.fetch(
        key=key,
        building_name="대치아파트",
        dong_name="101동",
    )

    assert result.title_count == 2
    assert result.selected_title["dongNm"] == "101"

    values = result.feature_values

    assert values["연면적(㎡)"] == 11667.18
    assert values["사용승인연도"] == 1991
    assert (
        values["건축물대장_원천_표제부_최고지상층수"]
        == 15
    )
    assert (
        values[
            "건축물대장_원천_건축물_최종세대호수"
        ]
        == 327
    )
    assert (
        values["건축물대장_원천_대표구조"]
        == "철근콘크리트구조"
    )

    print("건축물대장 Service 검증 완료")
    print("- Client 결과 수신")
    print("- 대상 표제부 선택")
    print("- Feature 변환")


if __name__ == "__main__":
    main()