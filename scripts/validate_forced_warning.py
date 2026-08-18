from app.diagnosis.forced_warning import (
    ForcedWarningInput,
    ForcedWarningRule,
)
from app.diagnosis.schemas import RiskGrade


def main() -> None:
    normal = ForcedWarningRule.apply(
        RiskGrade.LOW,
        ForcedWarningInput(False, False, False, False, False, False, True, False),
    )
    assert normal.grade == RiskGrade.LOW
    assert normal.warnings == ()
    assert normal.missing_checks == ()

    landlord = ForcedWarningRule.apply(
        RiskGrade.LOW,
        ForcedWarningInput(False, False, False, False, False, False, True, True),
    )
    assert landlord.grade == RiskGrade.HIGH
    assert landlord.warnings == ("BAD_LANDLORD_MATCH",)

    auction = ForcedWarningRule.apply(
        RiskGrade.MEDIUM,
        ForcedWarningInput(False, False, False, True, False, False, True, False),
    )
    assert auction.grade == RiskGrade.CRITICAL
    assert auction.warnings == ("AUCTION_COMMENCED",)

    unknown = ForcedWarningRule.apply(
        RiskGrade.MEDIUM,
        ForcedWarningInput(None, None, None, None, None, None, None, None),
    )
    assert unknown.grade == RiskGrade.MEDIUM
    assert "AUCTION_COMMENCED" in unknown.missing_checks
    assert "BAD_LANDLORD_WATCHLIST" in unknown.missing_checks
    assert "OWNER_MATCH" in unknown.missing_checks

    print("강제경고 Rule 검증 완료")
    print(f"- 정상 등급: {normal.grade.value}")
    print(f"- 악성임대인 등급: {landlord.grade.value}")
    print(f"- 경매개시 등급: {auction.grade.value}")
    print(f"- 미확인 항목: {unknown.missing_checks}")


if __name__ == "__main__":
    main()
