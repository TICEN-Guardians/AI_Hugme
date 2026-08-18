from dataclasses import dataclass
from typing import Protocol

from app.diagnosis.external.address.schemas import ResolvedAddress
from app.diagnosis.schemas import HousingType


class PropertyMatchError(ValueError):
    pass


@dataclass(frozen=True)
class PropertyReference:
    district: str
    bun: str
    ji: str
    housing_type: HousingType
    model_name: str
    source_building_name: str = ""
    sample_count: int = 1


@dataclass(frozen=True)
class PropertyMatchResult:
    model_name: str
    method: str
    warnings: tuple[str, ...] = ()


class PropertyReferenceLookup(Protocol):
    def find_parcel(
        self,
        district: str,
        bun: str,
        ji: str,
        housing_type: HousingType,
    ) -> list[PropertyReference]: ...

    def find_district(
        self,
        district: str,
        housing_type: HousingType,
    ) -> list[PropertyReference]: ...

    def find_type(
        self,
        housing_type: HousingType,
    ) -> list[PropertyReference]: ...


class PropertyMatcher:
    def __init__(
        self,
        references: list[PropertyReference] | PropertyReferenceLookup,
    ) -> None:
        self.lookup = (
            references
            if not isinstance(references, list)
            else None
        )
        self.index: dict[
            tuple[str, str, str, HousingType],
            list[PropertyReference],
        ] = {}
        self.district_index: dict[
            tuple[str, HousingType],
            list[PropertyReference],
        ] = {}
        self.type_index: dict[
            HousingType,
            list[PropertyReference],
        ] = {}

        for reference in (
            references if isinstance(references, list) else []
        ):
            if reference.sample_count <= 0:
                raise PropertyMatchError("표본 수 오류")

            key = self._key(
                reference.district,
                reference.bun,
                reference.ji,
                reference.housing_type,
            )
            self.index.setdefault(key, []).append(reference)
            district_key = (
                self._district(reference.district),
                reference.housing_type,
            )
            self.district_index.setdefault(
                district_key,
                [],
            ).append(reference)
            self.type_index.setdefault(
                reference.housing_type,
                [],
            ).append(reference)

    def match(
        self,
        address: ResolvedAddress,
        housing_type: HousingType,
        observed_building_name: str | None = None,
    ) -> PropertyMatchResult:
        ledger_key = address.building_ledger_key
        key = self._key(
            address.district,
            ledger_key.bun,
            ledger_key.ji,
            housing_type,
        )
        references = (
            self.lookup.find_parcel(
                key[0],
                key[1],
                key[2],
                housing_type,
            )
            if self.lookup
            else self.index.get(key, [])
        )

        if not references:
            return self._missing_parcel(
                address,
                housing_type,
                observed_building_name,
            )

        names = {
            reference.model_name.strip()
            for reference in references
            if reference.model_name.strip()
        }

        if len(names) == 1:
            return PropertyMatchResult(
                model_name=names.pop(),
                method="parcel",
            )

        actual_name = str(
            observed_building_name
            or address.building_name
            or ""
        ).strip()
        building_name = self._name(actual_name)
        matched_names = {
            reference.model_name.strip()
            for reference in references
            if building_name
            and building_name == self._name(reference.model_name)
        }

        if matched_names:
            matched = [
                reference
                for reference in references
                if reference.model_name.strip()
                in matched_names
            ]
            return PropertyMatchResult(
                model_name=self._rank(matched),
                method="building_name",
            )

        if actual_name:
            return PropertyMatchResult(
                model_name=actual_name,
                method="ambiguous_observed_name",
                warnings=(
                    "PROPERTY_REFERENCE_AMBIGUOUS",
                    "UNSEEN_PROPERTY_NAME",
                ),
            )

        return PropertyMatchResult(
            model_name=self._rank(references),
            method="parcel_frequency",
            warnings=(
                "PROPERTY_REFERENCE_AMBIGUOUS",
                "PROPERTY_NAME_FALLBACK",
            ),
        )

    def _missing_parcel(
        self,
        address: ResolvedAddress,
        housing_type: HousingType,
        observed_building_name: str | None,
    ) -> PropertyMatchResult:
        name = str(
            observed_building_name
            or address.building_name
            or ""
        ).strip()

        if name:
            return PropertyMatchResult(
                model_name=name,
                method="unseen_address_name",
                warnings=("UNSEEN_PROPERTY_NAME",),
            )

        district_key = (
            self._district(address.district),
            housing_type,
        )
        district_references = (
            self.lookup.find_district(
                district_key[0],
                housing_type,
            )
            if self.lookup
            else self.district_index.get(district_key, [])
        )

        if district_references:
            return PropertyMatchResult(
                model_name=self._rank(district_references),
                method="district_frequency",
                warnings=(
                    "PROPERTY_REFERENCE_NOT_FOUND",
                    "PROPERTY_NAME_FALLBACK",
                ),
            )

        type_references = (
            self.lookup.find_type(housing_type)
            if self.lookup
            else self.type_index.get(housing_type, [])
        )

        if type_references:
            return PropertyMatchResult(
                model_name=self._rank(type_references),
                method="type_frequency",
                warnings=(
                    "PROPERTY_REFERENCE_NOT_FOUND",
                    "PROPERTY_NAME_FALLBACK",
                ),
            )

        raise PropertyMatchError("주택유형 기준정보 없음")

    @staticmethod
    def _rank(
        references: list[PropertyReference],
    ) -> str:
        counts: dict[str, int] = {}

        for reference in references:
            name = reference.model_name.strip()

            if name:
                counts[name] = (
                    counts.get(name, 0)
                    + reference.sample_count
                )

        if not counts:
            raise PropertyMatchError("학습 명칭 없음")

        return sorted(
            counts,
            key=lambda name: (-counts[name], name),
        )[0]

    @staticmethod
    def _key(
        district: str,
        bun: str,
        ji: str,
        housing_type: HousingType,
    ) -> tuple[str, str, str, HousingType]:
        return (
            PropertyMatcher._district(district),
            PropertyMatcher._number(bun),
            PropertyMatcher._number(ji),
            housing_type,
        )

    @staticmethod
    def _number(value: str) -> str:
        text = str(value).strip()

        if not text.isdigit():
            raise PropertyMatchError("지번 형식 오류")

        return text.zfill(4)

    @staticmethod
    def _district(value: str) -> str:
        return " ".join(str(value).split())

    @staticmethod
    def _name(value: str | None) -> str:
        return "".join(str(value or "").split()).lower()
