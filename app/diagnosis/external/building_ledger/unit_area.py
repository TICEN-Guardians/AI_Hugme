from dataclasses import dataclass
from typing import Any


class UnitAreaError(ValueError):
    pass


@dataclass(frozen=True)
class UnitAreaResult:
    dong_name: str
    ho_name: str
    floor: int
    exclusive_area: float
    common_area: float
    total_area: float
    row_count: int
    zero_area_count: int


class UnitAreaMapper:
    @classmethod
    def map(
        cls,
        items: list[dict[str, Any]],
        dong_name: str,
        ho_name: str,
    ) -> UnitAreaResult:
        dong = cls._normalize(dong_name, "동")
        ho = cls._normalize(ho_name, "호")

        selected = [
            item
            for item in items
            if cls._normalize(item.get("dongNm"), "동") == dong
            and cls._normalize(item.get("hoNm"), "호") == ho
        ]

        if not selected:
            raise UnitAreaError("동·호 면적 조회 결과 없음")

        exclusive_area = 0.0
        common_area = 0.0
        zero_area_count = 0
        floors: set[int] = set()

        for item in selected:
            area = cls._area(item.get("area"))
            category = str(
                item.get("exposPubuseGbCdNm") or ""
            ).strip()

            if area == 0:
                zero_area_count += 1

            if category == "전유":
                exclusive_area += area
                floors.add(cls._floor(item))
            elif category == "공용":
                common_area += area
            elif area > 0:
                raise UnitAreaError(
                    f"미지원 면적 구분: {category}"
                )

        if exclusive_area <= 0:
            raise UnitAreaError("전유면적 누락")

        if len(floors) != 1:
            raise UnitAreaError("전유부 층 불일치")

        exclusive_area = round(exclusive_area, 4)
        common_area = round(common_area, 4)

        return UnitAreaResult(
            dong_name=dong,
            ho_name=ho,
            floor=floors.pop(),
            exclusive_area=exclusive_area,
            common_area=common_area,
            total_area=round(
                exclusive_area + common_area,
                4,
            ),
            row_count=len(selected),
            zero_area_count=zero_area_count,
        )

    @staticmethod
    def _normalize(
        value: Any,
        suffix: str,
    ) -> str:
        text = "".join(str(value or "").split())

        if text.endswith(suffix):
            text = text[:-1]

        return text

    @staticmethod
    def _area(value: Any) -> float:
        try:
            area = float(value)
        except (TypeError, ValueError):
            raise UnitAreaError("면적 형식 오류") from None

        if area < 0:
            raise UnitAreaError("음수 면적")

        return area

    @staticmethod
    def _floor(item: dict[str, Any]) -> int:
        try:
            floor = int(item.get("flrNo"))
        except (TypeError, ValueError):
            raise UnitAreaError("층 형식 오류") from None

        floor_type = str(
            item.get("flrGbCdNm") or ""
        ).strip()

        if floor_type == "지하":
            return -abs(floor)

        if floor_type == "지상":
            return abs(floor)

        raise UnitAreaError("층 구분 오류")
