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
        """전유부 용도로 주택유형을 정한다.

        표제부 세부용도가 '공동주택' 처럼 뭉뚱그려 적힌 건물은
        resolve() 로 판정되지 않는다. 전유부에는 세대별 용도가
        '아파트', '오피스텔' 처럼 구체적으로 적혀 있어 이를 보완 경로로 쓴다.

        한 동에 상가와 주거가 섞여 있을 수 있으므로, 소수 항목이
        전체를 결정하지 않도록 과반을 넘는 용도만 인정한다.
        """
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
        """주용도와 세부용도를 한 덩어리로 보고 유형 단어를 찾는다.

        전유부는 두 필드에 용도가 나뉘어 담기는 경우가 있어
        (주용도='오피스텔', 세부용도='업무시설(오피스텔)') 둘을 함께 본다.
        """
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