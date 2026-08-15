from typing import Any


class BuildingLedgerMapper:
    @classmethod
    def map_title(
        cls,
        item: dict[str, Any],
    ) -> dict[str, str | int | float | None]:
        ride_elevator = cls._int(item.get("rideUseElvtCnt"))
        emergency_elevator = cls._int(
            item.get("emgenUseElvtCnt")
        )

        elevator_count = (
            (ride_elevator or 0)
            + (emergency_elevator or 0)
        )

        return {
            "연면적(㎡)": cls._float(item.get("totArea")),
            "대지면적(㎡)": cls._float(item.get("platArea")),
            "사용승인연도": cls._year(
                item.get("useAprDay")
            ),
            "건축물대장_원천_표제부_건폐율최대": (
                cls._float(item.get("bcRat"))
            ),
            "건축물대장_원천_표제부_최고지상층수": (
                cls._int(item.get("grndFlrCnt"))
            ),
            "건축물대장_원천_표제부_최대지하층수": (
                cls._int(item.get("ugrndFlrCnt"))
            ),
            "건축물대장_원천_표제부_승용승강기수합": (
                ride_elevator
            ),
            "건축물대장_원천_표제부_비상용승강기수합": (
                emergency_elevator
            ),
            "건축물대장_원천_건축물_최종세대호수": (
                cls._households(item)
            ),
            "건축물대장_승강기존재여부": int(
                elevator_count > 0
            ),
            "건축물대장_원천_대표구조": cls._text(
                item.get("strctCdNm")
            ),
            "건축물대장_원천_대표주용도": cls._text(
                item.get("mainPurpsCdNm")
            ),
            "건축물대장_내진설계적용여부_파생": (
                cls._text(item.get("rserthqkDsgnApplyYn"))
            ),
        }

    @classmethod
    def _households(
        cls,
        item: dict[str, Any],
    ) -> int | None:
        household_count = cls._int(item.get("hhldCnt"))
        family_count = cls._int(item.get("fmlyCnt"))

        if household_count is not None:
            return household_count

        return family_count

    @staticmethod
    def _text(value: Any) -> str | None:
        if value is None:
            return None

        text = str(value).strip()
        return text or None

    @staticmethod
    def _int(value: Any) -> int | None:
        if value in {None, ""}:
            return None

        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _float(value: Any) -> float | None:
        if value in {None, ""}:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _year(value: Any) -> int | None:
        if value is None:
            return None

        text = str(value).strip()

        if len(text) < 4 or not text[:4].isdigit():
            return None

        return int(text[:4])