from dataclasses import dataclass

from app.diagnosis.external.address.schemas import (ResolvedAddress,)
from app.diagnosis.external.address.service import (AddressService,)
from app.diagnosis.external.building_ledger.service import (BuildingLedgerResult,BuildingLedgerService,)
from app.diagnosis.housing_type_resolver import (HousingTypeResolver,)
from app.diagnosis.schemas import HousingType
from app.diagnosis.external.building_ledger.unit_area import (UnitAreaError,UnitAreaResult,)

class PropertyAddressError(ValueError):
    pass


@dataclass(frozen=True)
class PropertyAddressResult:
    address: ResolvedAddress
    building_ledger: BuildingLedgerResult
    dong_name: str | None
    ho_name: str | None
    housing_type: HousingType
    unit_area: UnitAreaResult | None


class PropertyAddressService:
    def __init__(
        self,
        address_service: AddressService,
        building_ledger_service: BuildingLedgerService,
    ) -> None:
        self.address_service = address_service
        self.building_ledger_service = (
            building_ledger_service
        )

    def resolve(
        self,
        address: str,
        dong_name: str | None,
        ho_name: str | None = None,
    ) -> PropertyAddressResult:
        resolved = self.address_service.resolve(address)

        self._validate_dong(
            requested=dong_name,
            available=resolved.available_dongs,
        )

        ledger_result = (
            self.building_ledger_service.fetch(
                key=resolved.building_ledger_key,
                building_name=resolved.building_name,
                dong_name=dong_name,
            )
        )
        housing_type = HousingTypeResolver.resolve(
            ledger_result.selected_title
        )

        if (
            housing_type != HousingType.DETACHED_MULTI
            and not dong_name
            and resolved.available_dongs
        ):
            raise PropertyAddressError("공동주택 동 정보 필요")

        unit_area = None

        if (
            housing_type != HousingType.DETACHED_MULTI
            and ho_name
        ):
            try:
                unit_area = (
                    self.building_ledger_service
                    .fetch_unit_area(
                        key=resolved.building_ledger_key,
                        dong_name=dong_name,
                        ho_name=ho_name,
                    )
                )
            except UnitAreaError:
                # 일부 건축물은 공공데이터 전유부에 동·호 면적이 없다.
                # 주소와 주택유형 확인은 유지하고, 추론 시 Feature 기본값을 쓴다.
                unit_area = None

        return PropertyAddressResult(
            address=resolved,
            building_ledger=ledger_result,
            dong_name=dong_name,
            ho_name=ho_name,
            housing_type=housing_type,
            unit_area=unit_area,
        )

    @classmethod
    def _validate_dong(
        cls,
        requested: str | None,
        available: tuple[str, ...],
    ) -> None:
        requested_value = cls._dong(requested)

        if not requested_value:
            return

        if not available:
            return

        available_values = {
            cls._dong(value)
            for value in available
        }

        if requested_value not in available_values:
            raise PropertyAddressError(
                f"주소에 존재하지 않는 동: "
                f"{requested}"
            )

    @staticmethod
    def _dong(value: str | None) -> str:
        text = "".join((value or "").split()).lower()

        if text.endswith("동"):
            return text[:-1]

        return text
