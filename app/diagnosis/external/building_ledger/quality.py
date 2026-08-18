from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BuildingLedgerQuality:
    blocking_errors: tuple[str, ...]
    warnings: tuple[str, ...]


class BuildingLedgerQualityGate:
    @classmethod
    def evaluate(
        cls,
        item: dict[str, Any],
    ) -> BuildingLedgerQuality:
        blocking = []
        warnings = []

        if not cls._positive(item.get("totArea")):
            blocking.append("TOTAL_AREA_MISSING")

        if not cls._year(item.get("useAprDay")):
            blocking.append("USE_APPROVAL_YEAR_MISSING")

        if not cls._positive(item.get("grndFlrCnt")):
            blocking.append("GROUND_FLOOR_COUNT_MISSING")

        if not cls._text(item.get("mainPurpsCdNm")):
            blocking.append("MAIN_PURPOSE_MISSING")

        if not cls._text(item.get("strctCdNm")):
            blocking.append("STRUCTURE_MISSING")

        if not cls._positive(item.get("platArea")):
            warnings.append("LAND_AREA_UNAVAILABLE")

        if not cls._positive(item.get("bcRat")):
            warnings.append("BUILDING_COVERAGE_RATIO_UNAVAILABLE")

        if not cls._positive(item.get("vlRat")):
            warnings.append("FLOOR_AREA_RATIO_UNAVAILABLE")

        if cls._missing(item.get("rideUseElvtCnt")):
            warnings.append("PASSENGER_ELEVATOR_COUNT_UNKNOWN")

        if cls._missing(item.get("emgenUseElvtCnt")):
            warnings.append("EMERGENCY_ELEVATOR_COUNT_UNKNOWN")

        if (
            cls._missing(item.get("hhldCnt"))
            and cls._missing(item.get("fmlyCnt"))
        ):
            warnings.append("HOUSEHOLD_COUNT_UNKNOWN")

        if cls._missing(
            item.get("rserthqkDsgnApplyYn")
        ):
            warnings.append("SEISMIC_DESIGN_UNKNOWN")

        return BuildingLedgerQuality(
            blocking_errors=tuple(blocking),
            warnings=tuple(warnings),
        )

    @staticmethod
    def _missing(value: Any) -> bool:
        return value is None or not str(value).strip()

    @staticmethod
    def _text(value: Any) -> str | None:
        if value is None:
            return None

        text = str(value).strip()
        return text or None

    @staticmethod
    def _positive(value: Any) -> bool:
        try:
            return float(value) > 0
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _year(value: Any) -> int | None:
        text = str(value or "").strip()

        if len(text) < 4 or not text[:4].isdigit():
            return None

        year = int(text[:4])

        if 1800 <= year <= 2100:
            return year

        return None