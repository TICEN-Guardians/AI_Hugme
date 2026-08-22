import math
import re
from datetime import date

from app.diagnosis.external.rtms.client import (
    RtmsApiError,
    RtmsClient,
)
from app.diagnosis.external.rtms.schemas import (
    ComparableBin,
    MarketComparableResult,
    RentTransaction,
)
from app.diagnosis.schemas import HousingType


class MarketComparableService:
    MIN_SAMPLE_COUNT = 5
    PRIMARY_MONTHS = 6
    EXPANDED_MONTHS = 12
    BIN_COUNT = 8

    def __init__(
        self,
        client: RtmsClient,
    ) -> None:
        self.client = client

    def analyze(
        self,
        housing_type: HousingType,
        district_code: str,
        district: str,
        building_name: str | None,
        area: float,
        contract_date: date,
        user_deposit: int,
    ) -> MarketComparableResult:
        anchor = min(contract_date, date.today())

        try:
            primary = self._load(
                housing_type,
                district_code,
                anchor,
                self.PRIMARY_MONTHS,
            )
            selected = self._select(
                primary,
                housing_type,
                district,
                building_name,
                area,
            )

            if selected is None:
                expanded = self._load(
                    housing_type,
                    district_code,
                    anchor,
                    self.EXPANDED_MONTHS,
                )
                selected = self._select(
                    expanded,
                    housing_type,
                    district,
                    building_name,
                    area,
                    expanded=True,
                )
        except RtmsApiError:
            return MarketComparableResult.unavailable(
                "RTMS_API_UNAVAILABLE"
            )

        if selected is None:
            return MarketComparableResult.unavailable(
                "RTMS_COMPARABLE_SAMPLE_INSUFFICIENT",
                status="INSUFFICIENT",
            )

        scope, transactions, warning = selected
        return self._summarize(
            scope=scope,
            transactions=transactions,
            user_deposit=user_deposit,
            warning=warning,
        )

    def _load(
        self,
        housing_type: HousingType,
        district_code: str,
        anchor: date,
        months: int,
    ) -> tuple[RentTransaction, ...]:
        transactions: list[RentTransaction] = []

        for deal_ym in self._months(anchor, months):
            transactions.extend(
                self.client.get_rent_transactions(
                    housing_type,
                    district_code,
                    deal_ym,
                )
            )

        return tuple(transactions)

    def _select(
        self,
        transactions: tuple[RentTransaction, ...],
        housing_type: HousingType,
        district: str,
        building_name: str | None,
        area: float,
        expanded: bool = False,
    ) -> tuple[
        str,
        tuple[RentTransaction, ...],
        str | None,
    ] | None:
        tolerance = max(
            area * (0.2 if expanded else 0.1),
            10.0 if expanded else 5.0,
        )
        area_matches = tuple(
            item
            for item in transactions
            if abs(item.area - area) <= tolerance
        )
        legal_dong_matches = tuple(
            item
            for item in area_matches
            if self._same_legal_dong(
                item.legal_dong,
                district,
            )
        )

        if (
            housing_type != HousingType.DETACHED_MULTI
            and building_name
        ):
            building_matches = tuple(
                item
                for item in legal_dong_matches
                if self._same_building(
                    item.building_name,
                    building_name,
                )
            )
            if len(building_matches) >= self.MIN_SAMPLE_COUNT:
                return (
                    "SAME_BUILDING",
                    building_matches,
                    "RTMS_PERIOD_EXPANDED" if expanded else None,
                )

        if len(legal_dong_matches) >= self.MIN_SAMPLE_COUNT:
            return (
                "SAME_LEGAL_DONG",
                legal_dong_matches,
                "RTMS_PERIOD_EXPANDED" if expanded else None,
            )

        if len(area_matches) >= self.MIN_SAMPLE_COUNT:
            warning = (
                "RTMS_AREA_AND_PERIOD_EXPANDED"
                if expanded
                else "RTMS_SCOPE_EXPANDED_TO_DISTRICT"
            )
            return (
                "SAME_DISTRICT",
                area_matches,
                warning,
            )

        return None

    @classmethod
    def _summarize(
        cls,
        scope: str,
        transactions: tuple[RentTransaction, ...],
        user_deposit: int,
        warning: str | None,
    ) -> MarketComparableResult:
        deposits = sorted(item.deposit for item in transactions)
        areas = [item.area for item in transactions]
        dates = [item.contract_date for item in transactions]
        warnings = (warning,) if warning else ()

        return MarketComparableResult(
            status="AVAILABLE",
            source="MOLIT_RTMS",
            scope=scope,
            sample_count=len(transactions),
            period_start=min(dates),
            period_end=max(dates),
            area_min=round(min(areas), 2),
            area_max=round(max(areas), 2),
            minimum=deposits[0],
            percentile_25=cls._percentile(deposits, 0.25),
            median=cls._percentile(deposits, 0.5),
            percentile_75=cls._percentile(deposits, 0.75),
            maximum=deposits[-1],
            user_deposit_percentile=round(
                sum(
                    1
                    for value in deposits
                    if value <= user_deposit
                )
                / len(deposits)
                * 100,
                1,
            ),
            bins=cls._bins(deposits),
            warnings=warnings,
        )

    @classmethod
    def _bins(
        cls,
        values: list[int],
    ) -> tuple[ComparableBin, ...]:
        minimum = values[0]
        maximum = values[-1]

        if minimum == maximum:
            return (
                ComparableBin(
                    lower_bound=minimum,
                    upper_bound=maximum,
                    count=len(values),
                ),
            )

        width = math.ceil(
            (maximum - minimum) / cls.BIN_COUNT
        )
        counts = [0] * cls.BIN_COUNT

        for value in values:
            index = min(
                (value - minimum) // width,
                cls.BIN_COUNT - 1,
            )
            counts[index] += 1

        return tuple(
            ComparableBin(
                lower_bound=minimum + width * index,
                upper_bound=(
                    maximum
                    if index == cls.BIN_COUNT - 1
                    else minimum + width * (index + 1)
                ),
                count=count,
            )
            for index, count in enumerate(counts)
        )

    @staticmethod
    def _percentile(
        values: list[int],
        ratio: float,
    ) -> int:
        position = (len(values) - 1) * ratio
        lower = math.floor(position)
        upper = math.ceil(position)

        if lower == upper:
            return values[lower]

        fraction = position - lower
        return round(
            values[lower] * (1 - fraction)
            + values[upper] * fraction
        )

    @staticmethod
    def _months(
        anchor: date,
        count: int,
    ) -> tuple[str, ...]:
        months: list[str] = []
        year = anchor.year
        month = anchor.month

        for _ in range(count):
            months.append(f"{year:04d}{month:02d}")
            month -= 1
            if month == 0:
                year -= 1
                month = 12

        return tuple(months)

    @classmethod
    def _same_legal_dong(
        cls,
        value: str | None,
        district: str,
    ) -> bool:
        normalized = cls._normalized(value)
        if not normalized:
            return False
        district_parts = {
            cls._normalized(part)
            for part in district.split()
        }
        return normalized in district_parts

    @classmethod
    def _same_building(
        cls,
        left: str | None,
        right: str | None,
    ) -> bool:
        normalized_left = cls._normalized(left)
        normalized_right = cls._normalized(right)
        return bool(
            normalized_left
            and normalized_right
            and normalized_left == normalized_right
        )

    @staticmethod
    def _normalized(
        value: str | None,
    ) -> str:
        return re.sub(
            r"[^0-9A-Za-z가-힣]",
            "",
            str(value or ""),
        ).lower()
