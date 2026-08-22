from app.diagnosis.forced_warning import (
    ForcedWarningInput,
    ForcedWarningRule,
)
from app.diagnosis.schemas import RiskGrade


def main() -> None:
    normal = ForcedWarningRule.apply(
        20,
        ForcedWarningInput(False, False, False, False, False, False, True, False),
        registry_required=True,
    )
    assert normal.score == 20
    assert normal.grade == RiskGrade.LOW
    assert normal.warnings == ()
    assert normal.missing_checks == ()
    assert normal.score_floor is None

    landlord = ForcedWarningRule.apply(
        20,
        ForcedWarningInput(False, False, False, False, False, False, True, True),
        registry_required=True,
    )
    assert landlord.score == 80
    assert landlord.grade == RiskGrade.CRITICAL
    assert landlord.warnings == ("BAD_LANDLORD_MATCH",)
    assert landlord.score_floor_applied is True

    auction = ForcedWarningRule.apply(
        40,
        ForcedWarningInput(False, False, False, True, False, False, True, False),
        registry_required=True,
    )
    assert auction.score == 80
    assert auction.grade == RiskGrade.CRITICAL
    assert auction.warnings == ("AUCTION_COMMENCED",)

    unknown = ForcedWarningRule.apply(
        40,
        ForcedWarningInput(None, None, None, None, None, None, None, None),
        registry_required=True,
    )
    assert unknown.score == 40
    assert unknown.grade == RiskGrade.MEDIUM
    assert "AUCTION_COMMENCED" in unknown.missing_checks
    assert "BAD_LANDLORD_WATCHLIST" in unknown.missing_checks
    assert "OWNER_MATCH" in unknown.missing_checks

    quick = ForcedWarningRule.apply(
        40,
        ForcedWarningInput(True, True, True, True, True, True, False, True),
        registry_required=False,
    )
    assert quick.score == 40
    assert quick.warnings == ()
    assert quick.missing_checks == ()

    print("중대 권리 점수 하한 규칙 검증 완료")
    print(f"- 정상 점수: {normal.score}")
    print(f"- 악성임대인 점수: {landlord.score}")
    print(f"- 경매개시 점수: {auction.score}")
    print(f"- 미확인 항목: {unknown.missing_checks}")


if __name__ == "__main__":
    main()
