from dataclasses import dataclass

from app.diagnosis.deposit_recommendation import (
    DepositRecommendationCalculator,
    DepositRecommendationResult,
)
from app.diagnosis.forced_warning import ForcedWarningRule
from app.diagnosis.risk_indicator import (
    RiskIndicatorCalculator,
    RiskIndicatorResult,
)
from app.diagnosis.risk_rule import (
    RiskRule,
    RiskScoreResult,
    RiskSeverityInput,
)
from app.diagnosis.schemas import DiagnosisMode, RiskGrade


@dataclass(frozen=True)
class WhatIfScenarioResult:
    estimated_sale_price: int
    estimated_lease_price: int
    deposit: int
    active_max_claim_amount: int | None
    indicators: RiskIndicatorResult
    score: RiskScoreResult
    final_score: int
    final_grade: RiskGrade
    score_floor: int | None
    floor_reasons: tuple[str, ...]
    rights_adjustment: int


@dataclass(frozen=True)
class DiagnosisWhatIfResult:
    baseline: WhatIfScenarioResult
    scenario: WhatIfScenarioResult
    score_change: int
    grade_changed: bool
    registry_blockers_remain: bool
    unresolved_risk_reasons: tuple[str, ...]
    deposit_recommendation: DepositRecommendationResult


class DiagnosisWhatIfCalculator:
    @classmethod
    def calculate(
        cls,
        mode: DiagnosisMode,
        estimated_sale_price: int,
        estimated_lease_price: int,
        baseline_deposit: int,
        scenario_deposit: int,
        sale_price_drop_rate: int,
        lease_price_drop_rate: int,
        active_max_claim_amount: int | None,
        remove_active_mortgage: bool,
        market_trend_score: int,
        unresolved_risk_reasons: tuple[str, ...],
        scenario_active_max_claim_amount: int | None = None,
    ) -> DiagnosisWhatIfResult:
        cls._validate(
            mode=mode,
            active_max_claim_amount=active_max_claim_amount,
            scenario_active_max_claim_amount=scenario_active_max_claim_amount,
            remove_active_mortgage=remove_active_mortgage,
            market_trend_score=market_trend_score,
        )
        severity_value = market_trend_score / RiskRule.LIMITS["market_trend"]
        severity = RiskSeverityInput(severity_value, severity_value)
        reasons = tuple(dict.fromkeys(unresolved_risk_reasons))
        baseline = cls._evaluate(
            mode=mode,
            estimated_sale_price=estimated_sale_price,
            estimated_lease_price=estimated_lease_price,
            deposit=baseline_deposit,
            active_max_claim_amount=active_max_claim_amount,
            severity=severity,
            unresolved_risk_reasons=reasons,
        )
        scenario_active_claim = (
            0
            if remove_active_mortgage
            else scenario_active_max_claim_amount
            if scenario_active_max_claim_amount is not None
            else active_max_claim_amount
        )
        scenario = cls._evaluate(
            mode=mode,
            estimated_sale_price=cls._apply_drop(
                estimated_sale_price,
                sale_price_drop_rate,
            ),
            estimated_lease_price=cls._apply_drop(
                estimated_lease_price,
                lease_price_drop_rate,
            ),
            deposit=scenario_deposit,
            active_max_claim_amount=scenario_active_claim,
            severity=severity,
            unresolved_risk_reasons=reasons,
        )
        recommendation = DepositRecommendationCalculator.calculate(
            mode=mode,
            estimated_sale_price=scenario.estimated_sale_price,
            estimated_lease_price=scenario.estimated_lease_price,
            current_deposit=scenario_deposit,
            active_max_claim_amount=scenario_active_claim,
            severity=severity,
            unresolved_risk_reasons=reasons,
        )

        return DiagnosisWhatIfResult(
            baseline=baseline,
            scenario=scenario,
            score_change=scenario.final_score - baseline.final_score,
            grade_changed=scenario.final_grade != baseline.final_grade,
            registry_blockers_remain=bool(reasons),
            unresolved_risk_reasons=reasons,
            deposit_recommendation=recommendation,
        )

    @staticmethod
    def _evaluate(
        mode: DiagnosisMode,
        estimated_sale_price: int,
        estimated_lease_price: int,
        deposit: int,
        active_max_claim_amount: int | None,
        severity: RiskSeverityInput,
        unresolved_risk_reasons: tuple[str, ...],
    ) -> WhatIfScenarioResult:
        indicators = RiskIndicatorCalculator.calculate(
            estimated_sale_price=estimated_sale_price,
            estimated_lease_price=estimated_lease_price,
            deposit=deposit,
            active_max_claim_amount=active_max_claim_amount,
            collateral_expected=mode == DiagnosisMode.DETAILED,
        )
        score = RiskRule.score(indicators, severity)
        rights_floor = (
            ForcedWarningRule.SCORE_FLOOR
            if unresolved_risk_reasons
            else None
        )
        final_score = max(score.total, rights_floor or 0)
        score_floor = max(
            (
                value
                for value in (score.policy_floor, rights_floor)
                if value is not None
            ),
            default=None,
        )
        floor_reasons = tuple(
            dict.fromkeys(
                (*score.floor_reasons, *unresolved_risk_reasons)
            )
        )

        return WhatIfScenarioResult(
            estimated_sale_price=estimated_sale_price,
            estimated_lease_price=estimated_lease_price,
            deposit=deposit,
            active_max_claim_amount=active_max_claim_amount,
            indicators=indicators,
            score=score,
            final_score=final_score,
            final_grade=RiskRule.grade(final_score),
            score_floor=score_floor,
            floor_reasons=floor_reasons,
            rights_adjustment=final_score - score.total,
        )

    @staticmethod
    def _apply_drop(value: int, drop_rate: int) -> int:
        return max(value * (100 - drop_rate) // 100, 1)

    @staticmethod
    def _validate(
        mode: DiagnosisMode,
        active_max_claim_amount: int | None,
        scenario_active_max_claim_amount: int | None,
        remove_active_mortgage: bool,
        market_trend_score: int,
    ) -> None:
        if not 0 <= market_trend_score <= RiskRule.LIMITS["market_trend"]:
            raise ValueError("시장 추세 점수가 허용 범위를 벗어났습니다")
        if mode == DiagnosisMode.QUICK and (
            active_max_claim_amount is not None
            or scenario_active_max_claim_amount is not None
        ):
            raise ValueError("간편진단에는 선순위 근저당을 포함할 수 없습니다")
        if remove_active_mortgage and active_max_claim_amount is None:
            raise ValueError("말소를 가정할 선순위 근저당을 확인하지 못했습니다")
