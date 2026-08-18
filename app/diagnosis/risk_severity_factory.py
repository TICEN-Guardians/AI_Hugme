from dataclasses import dataclass

from app.diagnosis.market_feature_service import MarketFeatureResult
from app.diagnosis.risk_rule import RiskSeverityInput
from app.diagnosis.schemas import HousingType


@dataclass(frozen=True)
class RiskSeverityResult:
    severity: RiskSeverityInput
    sale_price_change: float | None
    lease_price_change: float | None
    building_age: int | None


class RiskSeverityFactory:
    TYPE_RISK = {
        HousingType.APARTMENT: 0.0,
        HousingType.OFFICETEL: 0.4,
        HousingType.DETACHED_MULTI: 0.7,
        HousingType.VILLA: 1.0,
    }

    @classmethod
    def create(
        cls,
        housing_type: HousingType,
        sale_market: MarketFeatureResult,
        lease_market: MarketFeatureResult,
    ) -> RiskSeverityResult:
        sale_change = cls._number(
            sale_market.rone.values.get("RONE_가격지수_전월비")
        )
        lease_change = cls._number(
            lease_market.rone.values.get("RONE_가격지수_전월비")
        )
        approval_year = cls._number(
            sale_market.feature_input.building_ledger.get("사용승인연도")
        )
        building_age = (
            max(sale_market.feature_input.contract_date.year - int(approval_year), 0)
            if approval_year is not None
            else None
        )
        property_severity = (
            0.7 * cls.TYPE_RISK[housing_type]
            + 0.3 * cls._age_severity(building_age)
        )

        return RiskSeverityResult(
            severity=RiskSeverityInput(
                volatility=cls._movement_severity(sale_change),
                sale_price_decline=cls._decline_severity(sale_change),
                lease_price_decline=cls._decline_severity(lease_change),
                property=property_severity,
                market=cls._market_severity(sale_market),
            ),
            sale_price_change=sale_change,
            lease_price_change=lease_change,
            building_age=building_age,
        )

    @staticmethod
    def _movement_severity(value: float | None) -> float:
        if value is None:
            return 0.0
        return min(abs(value) / 2.0, 1.0)

    @staticmethod
    def _decline_severity(value: float | None) -> float:
        if value is None or value >= 0:
            return 0.0
        return min(abs(value) / 2.0, 1.0)

    @staticmethod
    def _age_severity(age: int | None) -> float:
        if age is None or age <= 10:
            return 0.0
        if age <= 20:
            return 0.25
        if age <= 30:
            return 0.5
        if age <= 40:
            return 0.75
        return 1.0

    @classmethod
    def _market_severity(cls, market: MarketFeatureResult) -> float:
        rates = [
            cls._number(market.cofix.values.get("신규취급액기준_COFIX")),
            cls._number(market.ecos.values.get("ECOS_주담대금리_적용값")),
        ]
        rate_severity = cls._average(
            cls._rate_severity(value)
            for value in rates
            if value is not None
        )
        kosis = market.kosis.values
        macro_severity = cls._average(
            value
            for value in (
                cls._negative_severity(kosis.get("KOSIS_건설기성액"), 5.0),
                cls._negative_severity(kosis.get("KOSIS_경제심리지수"), 5.0),
                cls._leading_index_severity(
                    kosis.get("KOSIS_선행지수_순환변동치")
                ),
            )
            if value is not None
        )
        available = [
            value for value in (rate_severity, macro_severity) if value is not None
        ]
        return cls._average(available) or 0.0

    @staticmethod
    def _rate_severity(value: float) -> float:
        if value <= 3.0:
            return 0.2
        if value <= 4.0:
            return 0.5
        if value <= 5.0:
            return 0.8
        return 1.0

    @classmethod
    def _negative_severity(
        cls,
        value: object,
        scale: float,
    ) -> float | None:
        number = cls._number(value)
        if number is None:
            return None
        return min(max(-number / scale, 0.0), 1.0)

    @classmethod
    def _leading_index_severity(cls, value: object) -> float | None:
        number = cls._number(value)
        if number is None:
            return None
        return min(max((100.0 - number) / 5.0, 0.0), 1.0)

    @staticmethod
    def _average(values) -> float | None:
        items = list(values)
        return sum(items) / len(items) if items else None

    @staticmethod
    def _number(value: object) -> float | None:
        if isinstance(value, (int, float)):
            return float(value)
        return None
