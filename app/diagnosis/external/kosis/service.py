from dataclasses import dataclass
from datetime import date

from app.diagnosis.external.kosis.store import KosisStore


@dataclass(frozen=True)
class KosisResult:
    values: dict[str, float]
    contract_month: str | None
    base_month: str | None
    warnings: tuple[str, ...]


class KosisService:
    def __init__(self, store: KosisStore) -> None:
        self.store = store

    def resolve(self, contract_date: date) -> KosisResult:
        target_month = contract_date.strftime("%Y-%m")
        selected = self.store.find_latest(target_month)

        if not selected:
            return KosisResult(
                values={},
                contract_month=None,
                base_month=None,
                warnings=("KOSIS_DATA_NOT_FOUND",),
            )

        warnings = set()

        if selected[0].contract_month < target_month:
            warnings.add("KOSIS_DATA_STALE")

        if any(item.provisional for item in selected):
            warnings.add("KOSIS_PROVISIONAL_VALUE")

        return KosisResult(
            values={item.feature_name: item.value for item in selected},
            contract_month=selected[0].contract_month,
            base_month=selected[0].base_month,
            warnings=tuple(sorted(warnings)),
        )
