from app.diagnosis.external.building_ledger.mapper import (
    BuildingLedgerMapper,
)


def main() -> None:
    item = {
        "totArea": "1234.5",
        "platArea": "500.0",
        "useAprDay": "20150312",
        "bcRat": "58.4",
        "grndFlrCnt": "15",
        "ugrndFlrCnt": "2",
        "rideUseElvtCnt": "3",
        "emgenUseElvtCnt": "1",
        "hhldCnt": "120",
        "fmlyCnt": "0",
        "strctCdNm": "철근콘크리트구조",
        "mainPurpsCdNm": "공동주택",
        "rserthqkDsgnApplyYn": "Y",
    }

    values = BuildingLedgerMapper.map_title(item)

    assert values["연면적(㎡)"] == 1234.5
    assert values["대지면적(㎡)"] == 500.0
    assert values["사용승인연도"] == 2015

    assert (
        values["건축물대장_원천_표제부_건폐율최대"]
        == 58.4
    )
    assert (
        values["건축물대장_원천_표제부_최고지상층수"]
        == 15
    )
    assert (
        values["건축물대장_원천_표제부_최대지하층수"]
        == 2
    )
    assert (
        values[
            "건축물대장_원천_표제부_승용승강기수합"
        ]
        == 3
    )
    assert (
        values[
            "건축물대장_원천_표제부_비상용승강기수합"
        ]
        == 1
    )
    assert (
        values[
            "건축물대장_원천_건축물_최종세대호수"
        ]
        == 120
    )
    assert values["건축물대장_승강기존재여부"] == 1
    assert (
        values["건축물대장_원천_대표구조"]
        == "철근콘크리트구조"
    )
    assert (
        values["건축물대장_원천_대표주용도"]
        == "공동주택"
    )
    assert (
        values["건축물대장_내진설계적용여부_파생"]
        == "Y"
    )

    print("건축물대장 Mapper 검증 완료")


if __name__ == "__main__":
    main()