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