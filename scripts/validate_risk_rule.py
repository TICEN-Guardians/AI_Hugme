from app.diagnosis.risk_indicator import RiskIndicatorCalculator
from app.diagnosis.risk_rule import RiskRule, RiskSeverityInput
from app.diagnosis.schemas import RiskGrade


def main() -> None:
    indicators = RiskIndicatorCalculator.calculate(
        estimated_sale_price=280_000_000,
        estimated_lease_price=170_000_000,
        deposit=200_000_000,
        active_max_claim_amount=100_000_000,
    )
    result = RiskRule.score(
        indicators,
        RiskSeverityInput(
            volatility=0.3,
            sale_price_decline=0.3,
            lease_price_decline=0.5,
            property=0.625,
            market=3 / 7,
        ),
    )

    assert result.underwater == 34
    assert result.rollover == 30
    assert result.property == 6
    assert result.market == 3
    assert result.total == 73
    assert result.grade == RiskGrade.HIGH
    assert result.single_risk_protected is True
    assert result.provisional_collateral_basis is False

    unknown = RiskIndicatorCalculator.calculate(
        estimated_sale_price=280_000_000,
        estimated_lease_price=170_000_000,
        deposit=200_000_000,
        active_max_claim_amount=None,
    )
    provisional = RiskRule.score(
        unknown,
        RiskSeverityInput(0.0, 0.0, 0.0, 0.0, 0.0),
    )
    assert provisional.provisional_collateral_basis is True
    assert RiskRule.grade(25) == RiskGrade.LOW
    assert RiskRule.grade(26) == RiskGrade.MEDIUM
    assert RiskRule.grade(51) == RiskGrade.HIGH
    assert RiskRule.grade(76) == RiskGrade.CRITICAL

    print("위험점수 Rule 검증 완료")
    print(f"- 담보부족: {result.underwater}/47")
    print(f"- 역전세: {result.rollover}/35")
    print(f"- 주택 특성: {result.property}/10")
    print(f"- 시장 상황: {result.market}/8")
    print(f"- 총점: {result.total}/100")
    print(f"- 등급: {result.grade.value}")
    print(f"- 단일 위험 보호: {result.single_risk_protected}")
    print(f"- 담보 기준 잠정 여부: {result.provisional_collateral_basis}")
    print(f"- 미확인 담보 기준 잠정 여부: {provisional.provisional_collateral_basis}")


if __name__ == "__main__":
    main()
