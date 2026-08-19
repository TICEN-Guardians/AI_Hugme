from dataclasses import dataclass

from app.diagnosis.external.address.service import (
    AddressService,
)
from app.diagnosis.external.building_ledger.client import (
    BuildingLedgerClient,
)
from app.diagnosis.external.building_ledger.schemas import (
    BuildingLedgerKey,
)
from app.diagnosis.housing_type_resolver import (
    HousingTypeResolutionError,
    HousingTypeResolver,
)
from app.diagnosis.schemas import HousingType


@dataclass(frozen=True)
class PropertyCandidateResult:
    building_name: str | None
    dong_name: str | None
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
            available_dongs=resolved.available_dongs,
            ledger_key=resolved.building_ledger_key,
        )

        return PropertySearchResult(
            normalized_address=resolved.road_address,
            building_name=resolved.building_name,
            candidates=candidates,
        )

    def _candidates(
        self,
        titles: list[dict],
        building_name: str | None,
        available_dongs: tuple[str, ...],
        ledger_key: BuildingLedgerKey,
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

            actual_name = self._clean(
                title.get("bldNm")
            )
            expected_name = self._clean(
                building_name
            )

            if (
                expected_name
                and expected_name not in actual_name
            ):
                continue

            try:
                housing_type = (
                    self._housing_type(title, ledger_key)
                )
            except HousingTypeResolutionError:
                continue

            dong_name = str(
                title.get("dongNm") or ""
            ).strip()

            if (
                not dong_name
                and available_dongs
                and housing_type != HousingType.DETACHED_MULTI
            ):
                continue

            key = (dong_name or actual_name, housing_type)

            results[key] = PropertyCandidateResult(
                building_name=str(
                    title.get("bldNm") or ""
                ).strip() or None,
                dong_name=dong_name or None,
                housing_type=housing_type,
            )

        return tuple(
            sorted(
                results.values(),
                key=lambda item: item.dong_name or "",
            )
        )

    def _housing_type(
        self,
        title: dict,
        ledger_key: BuildingLedgerKey,
    ) -> HousingType:
        """표제부로 판정하고, 안 되면 전유부 용도로 보완한다.

        표제부 세부용도가 '공동주택' 으로만 적힌 건물이 적지 않아,
        그대로 두면 후보에서 통째로 빠진다.
        """
        try:
            return HousingTypeResolver.resolve(title)
        except HousingTypeResolutionError:
            pass

        return HousingTypeResolver.resolve_units(
            self.building_ledger_client.get_unit_purposes(
                key=ledger_key,
                dong_name=title.get("dongNm"),
            )
        )

    @staticmethod
    def _clean(value: object) -> str:
        return "".join(
            str(value or "").split()
        ).lower()
