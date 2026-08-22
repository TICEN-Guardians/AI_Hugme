from dataclasses import dataclass


@dataclass(frozen=True)
class RiskIndicatorResult:
    lease_to_sale_rate: float
    lease_price_gap_rate: float
    collateral_burden_amount: int | None
    collateral_burden_rate: float | None
    recoverable_amount: int | None
    deposit_shortfall: int | None
    remaining_collateral_capacity: int | None
    price_drop_scenarios: dict[str, float] | None
    missing_checks: tuple[str, ...]
    collateral_expected: bool


class RiskIndicatorCalculator:
    @staticmethod
    def calculate(
        estimated_sale_price: int,
        estimated_lease_price: int,
        deposit: int,
        active_max_claim_amount: int | None,
        collateral_expected: bool,
    ) -> RiskIndicatorResult:
        if min(estimated_sale_price, estimated_lease_price, deposit) <= 0:
            raise ValueError("시세와 보증금은 양수 필요")
        if active_max_claim_amount is not None and active_max_claim_amount < 0:
            raise ValueError("채권최고액은 0 이상 필요")

        lease_to_sale_rate = deposit / estimated_sale_price
        lease_price_gap_rate = (
            deposit - estimated_lease_price
        ) / estimated_lease_price

        if active_max_claim_amount is None:
            return RiskIndicatorResult(
                lease_to_sale_rate=lease_to_sale_rate,
                lease_price_gap_rate=lease_price_gap_rate,
                collateral_burden_amount=None,
                collateral_burden_rate=None,
                recoverable_amount=None,
                deposit_shortfall=None,
                remaining_collateral_capacity=None,
                price_drop_scenarios=None,
                missing_checks=(
                    ("ACTIVE_MAX_CLAIM_AMOUNT",)
                    if collateral_expected
                    else ()
                ),
                collateral_expected=collateral_expected,
            )

        burden = active_max_claim_amount + deposit
        recoverable = estimated_sale_price - active_max_claim_amount
        scenarios = {
            f"drop_{drop}": burden / (estimated_sale_price * (1 - drop / 100))
            for drop in (0, 10, 20)
        }

        return RiskIndicatorResult(
            lease_to_sale_rate=lease_to_sale_rate,
            lease_price_gap_rate=lease_price_gap_rate,
            collateral_burden_amount=burden,
            collateral_burden_rate=burden / estimated_sale_price,
            recoverable_amount=recoverable,
            deposit_shortfall=max(deposit - recoverable, 0),
            remaining_collateral_capacity=estimated_sale_price - burden,
            price_drop_scenarios=scenarios,
            missing_checks=(),
            collateral_expected=collateral_expected,
        )
