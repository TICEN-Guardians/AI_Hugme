from dataclasses import dataclass
from datetime import date

from app.diagnosis.external.cofix.store import CofixStore


FEATURE_NAME = "신규취급액기준_COFIX"


@dataclass(frozen=True)
class CofixResult:
    values: dict[str, float]
    publication_date: date | None
    target_month: str | None
    warnings: tuple[str, ...]


class CofixService:
    def __init__(self, store: CofixStore) -> None:
        self.store = store

    def resolve(self, contract_date: date) -> CofixResult:
        selected = self.store.find_latest(contract_date)

        if selected is None:
            return CofixResult(
                values={},
                publication_date=None,
                target_month=None,
                warnings=("COFIX_DATA_NOT_FOUND",),
            )

        return CofixResult(
            values={FEATURE_NAME: selected.value},
            publication_date=selected.publication_date,
            target_month=selected.target_month,
            warnings=(),
        )
