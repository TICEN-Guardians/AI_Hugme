from dataclasses import dataclass

from app.diagnosis.external.address.service import (
    AddressAmbiguousError,
    AddressService,
)
from app.diagnosis.external.building_ledger.client import (
    BuildingLedgerClient,
)
from app.diagnosis.external.building_ledger.schemas import (
    BuildingLedgerKey,
)
from app.diagnosis.external.building_ledger.selector import (
    BuildingLedgerSelector,
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
class AddressCandidateResult:
    road_address: str
    jibun_address: str
    building_name: str | None


@dataclass(frozen=True)
class PropertySearchResult:
    normalized_address: str
    road_address: str | None
    jibun_address: str | None
    building_name: str | None
    candidates: tuple[PropertyCandidateResult, ...]
    address_candidates: tuple[
        AddressCandidateResult, ...
    ] = ()


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

    def suggest(
        self,
        address: str,
    ) -> tuple[AddressCandidateResult, ...]:
        return self._address_candidates(
            self.address_service.suggest(address, limit=10)
        )

    def search(
        self,
        address: str,
    ) -> PropertySearchResult:
        try:
            resolved = (
                self.address_service.resolve(address)
            )
        except AddressAmbiguousError as exc:
            return PropertySearchResult(
                normalized_address="",
                road_address=None,
                jibun_address=None,
                building_name=None,
                candidates=(),
                address_candidates=self._address_candidates(
                    exc.candidates
                ),
            )

        titles = self.building_ledger_client.get_title(
            resolved.building_ledger_key
        )

        candidates = self._candidates(
            titles=titles,
            building_name=resolved.building_name,
            ledger_key=resolved.building_ledger_key,
        )

        return PropertySearchResult(
            normalized_address=resolved.road_address,
            road_address=resolved.road_address,
            jibun_address=resolved.jibun_address,
            building_name=resolved.building_name,
            candidates=candidates,
        )

    @staticmethod
    def _address_candidates(
        items: tuple[dict, ...],
    ) -> tuple[AddressCandidateResult, ...]:
        return tuple(
            AddressCandidateResult(
                road_address=str(
                    item.get("roadAddr") or ""
                ).strip(),
                jibun_address=str(
                    item.get("jibunAddr") or ""
                ).strip(),
                building_name=str(
                    item.get("bdNm") or ""
                ).strip() or None,
            )
            for item in items
        )

    def _candidates(
        self,
        titles: list[dict],
        building_name: str | None,
        ledger_key: BuildingLedgerKey,
    ) -> tuple[PropertyCandidateResult, ...]:
        results: dict[
            tuple[str, HousingType],
            PropertyCandidateResult,
        ] = {}

        ledger_has_dong = any(
            str(item.get("dongNm") or "").strip()
            for item in titles
            if item.get("mainAtchGbCdNm") == "주건축물"
        )

        for title in titles:
            if (
                title.get("mainAtchGbCdNm")
                != "주건축물"
            ):
                continue

            actual_name = self._clean(
                title.get("bldNm")
            )

            if not BuildingLedgerSelector.matches_building_name(
                expected=building_name,
                actual=title.get("bldNm"),
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
                and ledger_has_dong
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
