from app.diagnosis.risk_indicator import RiskIndicatorCalculator
from app.diagnosis.risk_rule import RiskRule, RiskSeverityInput
from app.diagnosis.schemas import RiskGrade


def main() -> None:
    indicators = RiskIndicatorCalculator.calculate(
        estimated_sale_price=280_000_000,
        estimated_lease_price=170_000_000,
        deposit=200_000_000,
        active_max_claim_amount=100_000_000,
        collateral_expected=True,
    )
    result = RiskRule.score(
        indicators,
        RiskSeverityInput(
            sale_price_decline=0.3,
            lease_price_decline=0.5,
        ),
    )

    assert result.price_burden == 45
    assert result.lease_market_deviation == 45
    assert result.market_trend == 4
    assert result.base_total == 94
    assert result.policy_adjustment == 6
    assert result.total == 100
    assert result.grade == RiskGrade.CRITICAL
    assert result.policy_floor == 100
    assert result.floor_reasons == (
        "RECOVERY_SHORTFALL",
        "COMBINED_PRICE_RISK",
    )
    assert result.provisional_collateral_basis is False

    unknown = RiskIndicatorCalculator.calculate(
        estimated_sale_price=280_000_000,
        estimated_lease_price=170_000_000,
        deposit=200_000_000,
        active_max_claim_amount=None,
        collateral_expected=True,
    )
    provisional = RiskRule.score(
        unknown,
        RiskSeverityInput(0.0, 0.0),
    )
    assert provisional.provisional_collateral_basis is True
    assert RiskRule.policy_floor(1.0, 0.0) == (
        80,
        ("NO_RECOVERY_BUFFER",),
    )
    assert RiskRule.policy_floor(0.7, 0.25) == (
        80,
        ("EXTREME_LEASE_DEVIATION",),
    )
    assert RiskRule.policy_floor(0.8, 0.05) == (
        56,
        ("COMBINED_PRICE_RISK",),
    )
    assert RiskRule.grade(25) == RiskGrade.LOW
    assert RiskRule.grade(26) == RiskGrade.MEDIUM
    assert RiskRule.grade(55) == RiskGrade.MEDIUM
    assert RiskRule.grade(56) == RiskGrade.HIGH
    assert RiskRule.grade(79) == RiskGrade.HIGH
    assert RiskRule.grade(80) == RiskGrade.CRITICAL

    print("위험점수 규칙 검증 완료")
    print(f"- 기본 가중점수: {result.base_total}/100")
    print(f"- 가격 위험 조정: +{result.policy_adjustment}")
    print(f"- 최종점수: {result.total}/100")
    print(f"- 등급: {result.grade.value}")
    print(f"- 담보 기준 잠정 여부: {result.provisional_collateral_basis}")
    print(f"- 미확인 담보 기준 잠정 여부: {provisional.provisional_collateral_basis}")


if __name__ == "__main__":
    main()
