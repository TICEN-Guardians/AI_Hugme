from collections import Counter
from typing import Any

from app.diagnosis.schemas import HousingType


class HousingTypeResolutionError(ValueError):
    pass


class HousingTypeResolver:
    APARTMENT_WORDS = (
        "아파트",
    )
    VILLA_WORDS = (
        "연립주택",
        "다세대주택",
        "연립",
        "다세대",
    )
    OFFICETEL_WORDS = (
        "오피스텔",
    )
    DETACHED_WORDS = (
        "단독주택",
        "다가구주택",
        "다중주택",
        "다가구",
        "단독",
    )

    @classmethod
    def resolve(
        cls,
        title: dict[str, Any],
    ) -> HousingType:
        detail_purpose = cls._clean(
            title.get("etcPurps")
        )
        main_purpose = cls._clean(
            title.get("mainPurpsCdNm")
        )

        if cls._contains(
            detail_purpose,
            cls.OFFICETEL_WORDS,
        ):
            return HousingType.OFFICETEL

        if cls._contains(
            detail_purpose,
            cls.VILLA_WORDS,
        ):
            return HousingType.VILLA

        if cls._contains(
            detail_purpose,
            cls.APARTMENT_WORDS,
        ):
            return HousingType.APARTMENT

        if cls._contains(
            detail_purpose,
            cls.DETACHED_WORDS,
        ):
            return HousingType.DETACHED_MULTI

        if cls._contains(
            main_purpose,
            ("단독주택",),
        ):
            return HousingType.DETACHED_MULTI

        raise HousingTypeResolutionError(
            "지원 주택유형 판정 불가: "
            f"주용도={main_purpose or '누락'}, "
            f"세부용도={detail_purpose or '누락'}"
        )

    @classmethod
    def resolve_units(
        cls,
        units: list[dict[str, Any]],
    ) -> HousingType:
        exclusive = [
            unit
            for unit in units
            if str(
                unit.get("exposPubuseGbCdNm") or ""
            ).strip() == "전유"
        ]

        if not exclusive:
            raise HousingTypeResolutionError(
                "전유부 전유 항목 없음"
            )

        votes: Counter[HousingType] = Counter()

        for unit in exclusive:
            housing_type = cls._match(
                unit.get("mainPurpsCdNm"),
                unit.get("etcPurps"),
            )

            if housing_type:
                votes[housing_type] += 1

        if not votes:
            raise HousingTypeResolutionError(
                "전유부 용도로 주택유형 판정 불가"
            )

        housing_type, count = votes.most_common(1)[0]

        if count * 2 <= len(exclusive):
            raise HousingTypeResolutionError(
                f"전유부 주거 용도 과반 미달: "
                f"{housing_type.value} "
                f"{count}/{len(exclusive)}"
            )

        return housing_type

    @classmethod
    def _match(
        cls,
        *values: Any,
    ) -> HousingType | None:
        text = "".join(cls._clean(value) for value in values)

        if cls._contains(text, cls.OFFICETEL_WORDS):
            return HousingType.OFFICETEL

        if cls._contains(text, cls.VILLA_WORDS):
            return HousingType.VILLA

        if cls._contains(text, cls.APARTMENT_WORDS):
            return HousingType.APARTMENT

        if cls._contains(text, cls.DETACHED_WORDS):
            return HousingType.DETACHED_MULTI

        return None

    @staticmethod
    def _contains(
        value: str,
        words: tuple[str, ...],
    ) -> bool:
        return any(
            word in value
            for word in words
        )

    @staticmethod
    def _clean(value: Any) -> str:
        return "".join(
            str(value or "").split()
        )