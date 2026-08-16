from dataclasses import dataclass

from app.diagnosis.external.address.service import (
    AddressService,
)
from app.diagnosis.external.building_ledger.client import (
    BuildingLedgerClient,
)
from app.diagnosis.housing_type_resolver import (
    HousingTypeResolutionError,
    HousingTypeResolver,
)
from app.diagnosis.schemas import HousingType


@dataclass(frozen=True)
class PropertyCandidateResult:
    building_name: str
    dong_name: str
    housing_type: HousingType


@dataclass(frozen=True)
class PropertySearchResult:
    normalized_address: str
    building_name: str | None
    candidates: tuple[PropertyCandidateResult, ...]


class PropertySearchService:
    def __init__(
        self,
        address_service: AddressService,
        building_ledger_client: BuildingLedgerClient,
    ) -> None:
        self.address_service = address_service
        self.building_ledger_client = (
            building_ledger_client
        )

    def search(
        self,
        address: str,
    ) -> PropertySearchResult:
        resolved = self.address_service.resolve(address)

        titles = self.building_ledger_client.get_title(
            resolved.building_ledger_key
        )

        candidates = self._candidates(
            titles=titles,
            building_name=resolved.building_name,
        )

        return PropertySearchResult(
            normalized_address=resolved.road_address,
            building_name=resolved.building_name,
            candidates=candidates,
        )

    @classmethod
    def _candidates(
        cls,
        titles: list[dict],
        building_name: str | None,
    ) -> tuple[PropertyCandidateResult, ...]:
        results: dict[
            tuple[str, HousingType],
            PropertyCandidateResult,
        ] = {}

        for title in titles:
            if (
                title.get("mainAtchGbCdNm")
                != "주건축물"
            ):
                continue

            actual_name = cls._clean(
                title.get("bldNm")
            )
            expected_name = cls._clean(
                building_name
            )

            if (
                expected_name
                and expected_name not in actual_name
            ):
                continue

            try:
                housing_type = (
                    HousingTypeResolver.resolve(title)
                )
            except HousingTypeResolutionError:
                continue

            dong_name = str(
                title.get("dongNm") or ""
            ).strip()

            if not dong_name:
                continue

            key = (dong_name, housing_type)

            results[key] = PropertyCandidateResult(
                building_name=str(
                    title.get("bldNm") or ""
                ).strip(),
                dong_name=dong_name,
                housing_type=housing_type,
            )

        return tuple(
            sorted(
                results.values(),
                key=lambda item: item.dong_name,
            )
        )

    @staticmethod
    def _clean(value: object) -> str:
        return "".join(
            str(value or "").split()
        ).lower()