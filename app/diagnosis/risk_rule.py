from dataclasses import dataclass

from app.diagnosis.risk_indicator import RiskIndicatorResult
from app.diagnosis.schemas import RiskGrade


@dataclass(frozen=True)
class RiskSeverityInput:
    volatility: float
    sale_price_decline: float
    lease_price_decline: float
    property: float
    market: float


@dataclass(frozen=True)
class RiskScoreResult:
    underwater: int
    rollover: int
    property: int
    market: int
    total: int
    grade: RiskGrade
    single_risk_protected: bool
    provisional_collateral_basis: bool


class RiskRule:
    LIMITS = {
        "underwater": 47,
        "rollover": 35,
        "property": 10,
        "market": 8,
    }

    @classmethod
    def score(
        cls,
        indicators: RiskIndicatorResult,
        severity: RiskSeverityInput,
    ) -> RiskScoreResult:
        cls._validate_severity(severity)
        dtv = (
            indicators.collateral_burden_rate
            if indicators.collateral_burden_rate is not None
            else indicators.lease_to_sale_rate
        )
        underwater_raw = 47 * (
            0.6 * cls.dtv_severity(dtv)
            + 0.2 * severity.volatility
            + 0.2 * severity.sale_price_decline
        )
        rollover_raw = 35 * (
            0.7 * cls.gap_severity(indicators.lease_price_gap_rate)
            + 0.3 * severity.lease_price_decline
        )
        raw_scores = {
            "underwater": underwater_raw,
            "rollover": rollover_raw,
            "property": 10 * severity.property,
            "market": 8 * severity.market,
        }
        scores = {name: round(value) for name, value in raw_scores.items()}
        total = min(sum(scores.values()), 100)
        grade = cls.grade(total)
        protected = any(
            raw_scores[name] / limit > 0.7
            for name, limit in cls.LIMITS.items()
        )
        if protected and grade == RiskGrade.LOW:
            grade = RiskGrade.MEDIUM
        elif protected and grade == RiskGrade.MEDIUM:
            grade = RiskGrade.HIGH

        return RiskScoreResult(
            **scores,
            total=total,
            grade=grade,
            single_risk_protected=protected,
            provisional_collateral_basis=(
                indicators.collateral_burden_rate is None
            ),
        )

    @staticmethod
    def dtv_severity(value: float) -> float:
        if value < 0.7:
            return 0.0
        if value < 0.8:
            return 0.4
        if value < 0.9:
            return 0.7
        if value <= 1.0:
            return 0.9
        return 1.0

    @staticmethod
    def gap_severity(value: float) -> float:
        if value < -0.05:
            return 0.0
        if value <= 0.05:
            return 0.3
        if value <= 0.15:
            return 0.7
        return 1.0

    @staticmethod
    def grade(score: int) -> RiskGrade:
        if score <= 25:
            return RiskGrade.LOW
        if score <= 50:
            return RiskGrade.MEDIUM
        if score <= 75:
            return RiskGrade.HIGH
        return RiskGrade.CRITICAL

    @staticmethod
    def _validate_severity(severity: RiskSeverityInput) -> None:
        for name, value in severity.__dict__.items():
            if not 0 <= value <= 1:
                raise ValueError(f"{name} 심각도는 0 이상 1 이하 필요")
