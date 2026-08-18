from datetime import date
from decimal import Decimal

from app.diagnosis.feature_input import FeatureInput
from app.diagnosis.property_address_service import PropertyAddressResult
from app.diagnosis.schemas import HousingType


class PropertyFeatureFactory:
    MODEL_TYPES = {
        "단독다가구": HousingType.DETACHED_MULTI,
        "아파트": HousingType.APARTMENT,
        "연립다세대": HousingType.VILLA,
        "오피스텔": HousingType.OFFICETEL,
    }
    HOUSING_LABELS = {
        HousingType.APARTMENT: "아파트",
        HousingType.VILLA: "연립다세대",
        HousingType.OFFICETEL: "오피스텔",
    }

    @classmethod
    def create(
        cls,
        result: PropertyAddressResult,
        model_key: str,
        contract_date: date,
        matched_name: str | None = None,
        contract_area: Decimal | None = None,
        exclusive_area: Decimal | None = None,
        floor: int | None = None,
        land_right_area: Decimal | None = None,
    ) -> FeatureInput:
        cls._validate_model_type(result, model_key)
        detail = {}

        if exclusive_area is not None:
            cls._put_area(detail, "전용면적(㎡)", exclusive_area)
        elif result.unit_area:
            detail["전용면적(㎡)"] = result.unit_area.exclusive_area

        if floor is not None:
            detail["층"] = floor
        elif result.unit_area:
            detail.update({
                "층": result.unit_area.floor,
            })

        cls._put_area(detail, "계약면적(㎡)", contract_area)
        cls._put_area(detail, "대지권면적(㎡)", land_right_area)

        match = {}

        name = (matched_name or "").strip()

        if name:
            key = (
                "건물명"
                if result.housing_type == HousingType.VILLA
                else "단지명"
            )
            match[key] = name

        return FeatureInput(
            contract_date=contract_date,
            normalized_address=result.address.road_address,
            district=result.address.district,
            housing_type=cls._housing_label(
                result,
                model_key,
            ),
            property_detail=detail,
            property_match=match,
            building_ledger=dict(
                result.building_ledger.feature_values
            ),
        )

    @staticmethod
    def _put_area(
        values: dict[str, object],
        name: str,
        area: Decimal | None,
    ) -> None:
        if area is None:
            return

        if area <= 0:
            raise ValueError(f"{name}은 0보다 커야 함")

        values[name] = float(area)

    @classmethod
    def _validate_model_type(
        cls,
        result: PropertyAddressResult,
        model_key: str,
    ) -> None:
        model_type = model_key.split("_", 1)[-1]
        expected = cls.MODEL_TYPES.get(model_type)

        if expected is None:
            raise ValueError(f"모델 키 오류: {model_key}")

        if expected != result.housing_type:
            raise ValueError("모델과 주택유형 불일치")

    @staticmethod
    def _housing_label(
        result: PropertyAddressResult,
        model_key: str,
    ) -> str:
        if result.housing_type != HousingType.DETACHED_MULTI:
            return PropertyFeatureFactory.HOUSING_LABELS[
                result.housing_type
            ]

        if model_key.startswith("전세_"):
            return "단독다가구"

        title = result.building_ledger.selected_title
        purpose = " ".join(
            str(title.get(name) or "")
            for name in ("etcPurps", "mainPurpsCdNm")
        )

        if "다가구" in purpose:
            return "다가구"

        if "단독" in purpose:
            return "단독"

        raise ValueError("단독·다가구 세부유형 판정 불가")
