from app.diagnosis.external.building_ledger.selector import (
    BuildingLedgerSelectionError,
    BuildingLedgerSelector,
)


def main() -> None:
    items = [
        {
            "mainAtchGbCdNm": "주건축물",
            "dongNm": "101",
            "bldNm": "대치아파트101동",
            "hhldCnt": 327,
        },
        {
            "mainAtchGbCdNm": "주건축물",
            "dongNm": "301",
            "bldNm": "대청아파트301동",
            "hhldCnt": 161,
        },
        {
            "mainAtchGbCdNm": "주건축물",
            "dongNm": "대치아파트단지내상가",
            "bldNm": "대치아파트단지내상가",
            "hhldCnt": 0,
        },
        {
            "mainAtchGbCdNm": "부속건축물",
            "dongNm": "통합경비실-1",
            "bldNm": "대치단지",
            "hhldCnt": 0,
        },
    ]

    selected = BuildingLedgerSelector.select_title(
        items=items,
        building_name="대치아파트",
        dong_name="101동",
    )

    assert selected["dongNm"] == "101"
    assert selected["bldNm"] == "대치아파트101동"
    assert selected["hhldCnt"] == 327

    try:
        BuildingLedgerSelector.select_title(
            items=items,
            building_name="대치아파트",
            dong_name="999동",
        )
    except BuildingLedgerSelectionError:
        pass
    else:
        raise AssertionError(
            "후보 없음 검증 실패"
        )

    print("건축물대장 Selector 검증 완료")
    print("- 건물명 일치")
    print("- 동 번호 일치")
    print("- 부속건축물 제외")
    print("- 후보 없음 차단")


if __name__ == "__main__":
    main()