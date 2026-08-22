from dataclasses import dataclass

from app.diagnosis.market_feature_service import MarketFeatureResult
from app.diagnosis.risk_rule import RiskSeverityInput


@dataclass(frozen=True)
class RiskSeverityResult:
    severity: RiskSeverityInput
    sale_price_change: float | None
    lease_price_change: float | None


class RiskSeverityFactory:
    @classmethod
    def create(
        cls,
        sale_market: MarketFeatureResult,
        lease_market: MarketFeatureResult,
    ) -> RiskSeverityResult:
        sale_change = cls._number(
            sale_market.rone.values.get("RONE_가격지수_전월비")
        )
        lease_change = cls._number(
            lease_market.rone.values.get("RONE_가격지수_전월비")
        )

        return RiskSeverityResult(
            severity=RiskSeverityInput(
                sale_price_decline=cls._decline_severity(sale_change),
                lease_price_decline=cls._decline_severity(lease_change),
            ),
            sale_price_change=sale_change,
            lease_price_change=lease_change,
        )

    @staticmethod
    def _decline_severity(value: float | None) -> float:
        if value is None or value >= 0:
            return 0.0
        return min(abs(value) / 2.0, 1.0)

    @staticmethod
    def _number(value: object) -> float | None:
        if isinstance(value, (int, float)):
            return float(value)
        return None
