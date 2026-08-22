from dataclasses import dataclass

from app.diagnosis.risk_indicator import RiskIndicatorResult
from app.diagnosis.schemas import RiskGrade


@dataclass(frozen=True)
class RiskSeverityInput:
    sale_price_decline: float
    lease_price_decline: float


@dataclass(frozen=True)
class RiskScoreResult:
    price_burden: int
    lease_market_deviation: int
    market_trend: int
    policy_adjustment: int
    base_total: int
    total: int
    grade: RiskGrade
    policy_floor: int | None
    floor_reasons: tuple[str, ...]
    provisional_collateral_basis: bool


class RiskRule:
    LIMITS = {
        "price_burden": 45,
        "lease_market_deviation": 45,
        "market_trend": 10,
    }

    DTV_SAFE_MAX = 0.7
    DTV_CAUTION_MAX = 0.8
    DTV_DANGER_MAX = 0.9
    DTV_CRITICAL_MAX = 1.0

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
        price_burden = round(
            cls.LIMITS["price_burden"] * cls.dtv_severity(dtv)
        )
        lease_market_deviation = round(
            cls.LIMITS["lease_market_deviation"]
            * cls.gap_severity(indicators.lease_price_gap_rate)
        )
        market_trend = round(
            cls.LIMITS["market_trend"]
            * (severity.sale_price_decline + severity.lease_price_decline)
            / 2
        )
        base_total = min(
            price_burden + lease_market_deviation + market_trend,
            100,
        )
        policy_floor, floor_reasons = cls.policy_floor(
            dtv,
            indicators.lease_price_gap_rate,
        )
        total = max(base_total, policy_floor or 0)

        return RiskScoreResult(
            price_burden=price_burden,
            lease_market_deviation=lease_market_deviation,
            market_trend=market_trend,
            policy_adjustment=total - base_total,
            base_total=base_total,
            total=total,
            grade=cls.grade(total),
            policy_floor=policy_floor,
            floor_reasons=floor_reasons,
            provisional_collateral_basis=(
                indicators.collateral_expected
                and indicators.collateral_burden_rate is None
            ),
        )

    @classmethod
    def dtv_severity(cls, value: float) -> float:
        if value < cls.DTV_SAFE_MAX:
            return 0.0
        if value < cls.DTV_CAUTION_MAX:
            return 0.4
        if value < cls.DTV_DANGER_MAX:
            return 0.7
        if value <= cls.DTV_CRITICAL_MAX:
            return 0.9
        return 1.0

    @classmethod
    def dtv_verdict(cls, value: float) -> str:
        if value < cls.DTV_SAFE_MAX:
            return "SAFE"
        if value < cls.DTV_CAUTION_MAX:
            return "CAUTION"
        return "RISK"

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
    def policy_floor(
        burden_rate: float,
        lease_gap_rate: float,
    ) -> tuple[int | None, tuple[str, ...]]:
        floor = None
        reasons = []
        if burden_rate > 1.0:
            floor = 100
            reasons.append("RECOVERY_SHORTFALL")
        elif burden_rate >= 1.0:
            floor = 80
            reasons.append("NO_RECOVERY_BUFFER")
        if lease_gap_rate >= 0.25:
            floor = max(floor or 0, 80)
            reasons.append("EXTREME_LEASE_DEVIATION")
        if burden_rate >= 0.8 and lease_gap_rate >= 0.05:
            floor = max(floor or 0, 56)
            reasons.append("COMBINED_PRICE_RISK")
        return floor, tuple(reasons)

    @staticmethod
    def grade(score: int) -> RiskGrade:
        if score <= 25:
            return RiskGrade.LOW
        if score <= 55:
            return RiskGrade.MEDIUM
        if score <= 79:
            return RiskGrade.HIGH
        return RiskGrade.CRITICAL

    @staticmethod
    def _validate_severity(severity: RiskSeverityInput) -> None:
        for name, value in severity.__dict__.items():
            if not 0 <= value <= 1:
                raise ValueError(f"{name} 심각도는 0 이상 1 이하 필요")
