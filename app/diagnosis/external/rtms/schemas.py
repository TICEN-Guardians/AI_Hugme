from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class RentTransaction:
    deposit: int
    area: float
    contract_date: date
    legal_dong: str | None
    building_name: str | None


@dataclass(frozen=True)
class ComparableBin:
    lower_bound: int
    upper_bound: int
    count: int


@dataclass(frozen=True)
class MarketComparableResult:
    status: str
    source: str
    scope: str | None
    sample_count: int
    period_start: date | None
    period_end: date | None
    area_min: float | None
    area_max: float | None
    minimum: int | None
    percentile_25: int | None
    median: int | None
    percentile_75: int | None
    maximum: int | None
    user_deposit_percentile: float | None
    bins: tuple[ComparableBin, ...]
    warnings: tuple[str, ...]

    @classmethod
    def unavailable(
        cls,
        warning: str,
        status: str = "UNAVAILABLE",
    ) -> "MarketComparableResult":
        return cls(
            status=status,
            source="MOLIT_RTMS",
            scope=None,
            sample_count=0,
            period_start=None,
            period_end=None,
            area_min=None,
            area_max=None,
            minimum=None,
            percentile_25=None,
            median=None,
            percentile_75=None,
            maximum=None,
            user_deposit_percentile=None,
            bins=(),
            warnings=(warning,),
        )
