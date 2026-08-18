from dataclasses import dataclass
from datetime import date

from app.diagnosis.external.rone.store import RoneStore, RoneValue


MODEL_TYPES = {
    "단독다가구": "단독주택",
    "아파트": "아파트",
    "연립다세대": "연립다세대",
    "오피스텔": "오피스텔",
}
MODEL_FEATURES = {
    "매매_단독다가구": (
        "RONE_중위단위가격_천원㎡",
        "RONE_가격지수",
        "RONE_가격지수_전월비",
    ),
    "매매_아파트": (
        "RONE_가격지수",
        "RONE_가격지수_전월비",
        "RONE_중위단위가격_천원㎡",
    ),
    "매매_연립다세대": (
        "RONE_가격지수_전월비",
        "RONE_중위단위가격_천원㎡",
    ),
    "매매_오피스텔": (
        "RONE_평균단위가격_천원㎡",
        "RONE_가격지수",
        "RONE_가격지수_전월비",
    ),
    "전세_단독다가구": (
        "RONE_중위단위가격_천원㎡",
        "RONE_가격지수",
        "RONE_가격지수_전월비",
    ),
    "전세_아파트": (
        "RONE_중위단위가격_천원㎡",
        "RONE_가격지수",
        "RONE_가격지수_전월비",
    ),
    "전세_연립다세대": (
        "RONE_중위단위가격_천원㎡",
        "RONE_가격지수",
        "RONE_가격지수_전월비",
    ),
    "전세_오피스텔": (
        "RONE_평균단위가격_천원㎡",
        "RONE_가격지수",
        "RONE_가격지수_전월비",
    ),
}


@dataclass(frozen=True)
class RoneResult:
    values: dict[str, float]
    base_months: dict[str, str]
    regions: dict[str, str]
    warnings: tuple[str, ...]


class RoneService:
    def __init__(self, store: RoneStore) -> None:
        self.store = store

    def resolve(
        self,
        model_key: str,
        district: str,
        contract_date: date,
        area: float | None,
    ) -> RoneResult:
        if model_key not in MODEL_FEATURES:
            raise ValueError(f"RONE 모델 키 오류: {model_key}")

        transaction_type, model_type = model_key.split("_", 1)
        housing_type = MODEL_TYPES[model_type]
        target_month = self._previous_month(contract_date)
        size_band = self._size_band(housing_type, area)
        region_names = self._region_names(district)
        values = {}
        base_months = {}
        regions = {}
        warnings = set()

        for feature_name in MODEL_FEATURES[model_key]:
            candidates = self.store.find_values(
                transaction_type,
                housing_type,
                size_band,
                feature_name,
                target_month,
            )
            selected = self._select(candidates, region_names)

            if selected is None:
                warnings.add("RONE_DATA_NOT_FOUND")
                continue

            values[feature_name] = selected.value
            base_months[feature_name] = selected.base_month
            regions[feature_name] = selected.region_name

            if selected.base_month < target_month:
                warnings.add("RONE_DATA_STALE")

            if selected.region_name != region_names[0]:
                warnings.add("RONE_REGION_FALLBACK")

        return RoneResult(
            values=values,
            base_months=base_months,
            regions=regions,
            warnings=tuple(sorted(warnings)),
        )

    def _region_names(self, district: str) -> tuple[str, ...]:
        tokens = str(district).split()
        province = self._province(tokens[0]) if tokens else "전국"
        local = tokens[1] if len(tokens) > 1 else province
        path = self.store.find_region_path(local)
        ordered = [local]

        for name in reversed(path):
            if name not in ordered:
                ordered.append(name)

        for name in (province, "전국"):
            if name not in ordered:
                ordered.append(name)

        return tuple(ordered)

    @staticmethod
    def _select(
        candidates: list[RoneValue],
        region_names: tuple[str, ...],
    ) -> RoneValue | None:
        for month in sorted(
            {item.base_month for item in candidates},
            reverse=True,
        ):
            monthly = {
                item.region_name: item
                for item in candidates
                if item.base_month == month
            }

            for region_name in region_names:
                if region_name in monthly:
                    return monthly[region_name]

        return None

    @staticmethod
    def _previous_month(value: date) -> str:
        year = value.year if value.month > 1 else value.year - 1
        month = value.month - 1 if value.month > 1 else 12
        return f"{year:04d}-{month:02d}"

    @staticmethod
    def _size_band(
        housing_type: str,
        area: float | None,
    ) -> str:
        if housing_type != "오피스텔" or area is None:
            return "전체"

        if area <= 40:
            return "40㎡이하"

        if area <= 60:
            return "40㎡초과 60㎡이하"

        if area <= 85:
            return "60㎡초과 85㎡이하"

        return "85㎡초과"

    @staticmethod
    def _province(value: str) -> str:
        aliases = {
            "서울특별시": "서울",
            "부산광역시": "부산",
            "대구광역시": "대구",
            "인천광역시": "인천",
            "광주광역시": "광주",
            "대전광역시": "대전",
            "울산광역시": "울산",
            "세종특별자치시": "세종",
            "제주특별자치도": "제주",
            "강원특별자치도": "강원",
            "전북특별자치도": "전북",
        }
        return aliases.get(value, value.removesuffix("도"))
