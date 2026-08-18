from dataclasses import dataclass
from datetime import date

from app.diagnosis.external.ecos.store import EcosStore


FEATURE_NAME = "ECOS_주담대금리_적용값"


@dataclass(frozen=True)
class EcosResult:
    values: dict[str, float]
    contract_month: str | None
    base_month: str | None
    warnings: tuple[str, ...]


class EcosService:
    def __init__(self, store: EcosStore) -> None:
        self.store = store

    def resolve(self, contract_date: date) -> EcosResult:
        target_month = contract_date.strftime("%Y-%m")
        selected = self.store.find_latest(target_month)

        if selected is None:
            return EcosResult(
                values={},
                contract_month=None,
                base_month=None,
                warnings=("ECOS_DATA_NOT_FOUND",),
            )

        warnings = set()

        if selected.contract_month < target_month:
            warnings.add("ECOS_DATA_STALE")

        if selected.provisional:
            warnings.add("ECOS_PROVISIONAL_VALUE")

        return EcosResult(
            values={FEATURE_NAME: selected.value},
            contract_month=selected.contract_month,
            base_month=selected.base_month,
            warnings=tuple(sorted(warnings)),
        )
