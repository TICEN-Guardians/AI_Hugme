from dataclasses import dataclass

from app.diagnosis.risk_indicator import RiskIndicatorCalculator
from app.diagnosis.risk_rule import RiskRule, RiskSeverityInput
from app.diagnosis.schemas import DiagnosisMode, RiskGrade


@dataclass(frozen=True)
class DepositRecommendationResult:
    recommended_limit: int
    reduction_required: int
    within_recommended_limit: bool
    target_score_max: int
    target_grade: RiskGrade
    score_at_limit: int
    calculation_basis: str
    registry_reflected: bool
    provisional: bool
    adjustment_can_resolve_final_risk: bool
    unresolved_risk_reasons: tuple[str, ...]


class DepositRecommendationCalculator:
    TARGET_SCORE_MAX = 25
    TARGET_GRADE = RiskGrade.LOW
    ROUND_UNIT = 1_000_000

    @classmethod
    def calculate(
        cls,
        mode: DiagnosisMode,
        estimated_sale_price: int,
        estimated_lease_price: int,
        current_deposit: int,
        active_max_claim_amount: int | None,
        severity: RiskSeverityInput,
        unresolved_risk_reasons: tuple[str, ...],
    ) -> DepositRecommendationResult:
        registry_reflected = (
            mode == DiagnosisMode.DETAILED
            and active_max_claim_amount is not None
        )
        provisional = not registry_reflected
        raw_limit = cls._maximum_low_risk_deposit(
            estimated_sale_price=estimated_sale_price,
            estimated_lease_price=estimated_lease_price,
            active_max_claim_amount=active_max_claim_amount,
            collateral_expected=mode == DiagnosisMode.DETAILED,
            severity=severity,
            search_upper=max(estimated_sale_price, current_deposit),
        )
        recommended_limit = cls._round_down(raw_limit)
        score_at_limit = cls._score(
            estimated_sale_price=estimated_sale_price,
            estimated_lease_price=estimated_lease_price,
            deposit=max(recommended_limit, 1),
            active_max_claim_amount=active_max_claim_amount,
            collateral_expected=mode == DiagnosisMode.DETAILED,
            severity=severity,
        )
        reasons = tuple(dict.fromkeys(unresolved_risk_reasons))

        return DepositRecommendationResult(
            recommended_limit=recommended_limit,
            reduction_required=max(current_deposit - recommended_limit, 0),
            within_recommended_limit=current_deposit <= recommended_limit,
            target_score_max=cls.TARGET_SCORE_MAX,
            target_grade=cls.TARGET_GRADE,
            score_at_limit=score_at_limit,
            calculation_basis=cls._basis(mode, registry_reflected),
            registry_reflected=registry_reflected,
            provisional=provisional,
            adjustment_can_resolve_final_risk=not reasons,
            unresolved_risk_reasons=reasons,
        )

    @classmethod
    def _maximum_low_risk_deposit(
        cls,
        estimated_sale_price: int,
        estimated_lease_price: int,
        active_max_claim_amount: int | None,
        collateral_expected: bool,
        severity: RiskSeverityInput,
        search_upper: int,
    ) -> int:
        low = 1
        high = max(search_upper, 1)
        best = 0

        while low <= high:
            middle = (low + high) // 2
            score = cls._score(
                estimated_sale_price=estimated_sale_price,
                estimated_lease_price=estimated_lease_price,
                deposit=middle,
                active_max_claim_amount=active_max_claim_amount,
                collateral_expected=collateral_expected,
                severity=severity,
            )
            if score <= cls.TARGET_SCORE_MAX:
                best = middle
                low = middle + 1
            else:
                high = middle - 1

        return best

    @staticmethod
    def _score(
        estimated_sale_price: int,
        estimated_lease_price: int,
        deposit: int,
        active_max_claim_amount: int | None,
        collateral_expected: bool,
        severity: RiskSeverityInput,
    ) -> int:
        indicators = RiskIndicatorCalculator.calculate(
            estimated_sale_price=estimated_sale_price,
            estimated_lease_price=estimated_lease_price,
            deposit=deposit,
            active_max_claim_amount=active_max_claim_amount,
            collateral_expected=collateral_expected,
        )
        return RiskRule.score(indicators, severity).total

    @classmethod
    def _round_down(cls, value: int) -> int:
        if value < cls.ROUND_UNIT:
            return value
        return value // cls.ROUND_UNIT * cls.ROUND_UNIT

    @staticmethod
    def _basis(mode: DiagnosisMode, registry_reflected: bool) -> str:
        if mode == DiagnosisMode.QUICK:
            return "PRICE_MARKET_ONLY"
        if registry_reflected:
            return "PRICE_MARKET_AND_REGISTRY"
        return "PRICE_MARKET_REGISTRY_UNCONFIRMED"
