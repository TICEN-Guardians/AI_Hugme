from app.diagnosis.risk_indicator import RiskIndicatorCalculator


def main() -> None:
    result = RiskIndicatorCalculator.calculate(
        estimated_sale_price=280_000_000,
        estimated_lease_price=170_000_000,
        deposit=200_000_000,
        active_max_claim_amount=100_000_000,
    )
    assert round(result.lease_to_sale_rate, 3) == 0.714
    assert round(result.lease_price_gap_rate, 3) == 0.176
    assert round(result.collateral_burden_rate or 0, 3) == 1.071
    assert result.recoverable_amount == 180_000_000
    assert result.deposit_shortfall == 20_000_000
    assert result.remaining_collateral_capacity == -20_000_000

    unknown = RiskIndicatorCalculator.calculate(
        estimated_sale_price=280_000_000,
        estimated_lease_price=170_000_000,
        deposit=200_000_000,
        active_max_claim_amount=None,
    )
    assert unknown.collateral_burden_rate is None
    assert unknown.missing_checks == ("ACTIVE_MAX_CLAIM_AMOUNT",)

    print("위험지표 검증 완료")
    print(f"- 전세가율: {result.lease_to_sale_rate:.3f}")
    print(f"- 보증금 괴리율: {result.lease_price_gap_rate:.3f}")
    print(f"- 담보부담률: {result.collateral_burden_rate:.3f}")
    print(f"- 보증금 부족액: {result.deposit_shortfall}")
    print(f"- 근저당 미확인: {unknown.missing_checks}")


if __name__ == "__main__":
    main()
