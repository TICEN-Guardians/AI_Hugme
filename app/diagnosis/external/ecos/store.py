import sqlite3
from dataclasses import dataclass
from pathlib import Path


class EcosStoreError(ValueError):
    pass


@dataclass(frozen=True)
class EcosValue:
    contract_month: str
    base_month: str
    value: float
    provisional: bool


class EcosStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._validate()

    def find_latest(self, contract_month: str) -> EcosValue | None:
        query = """
            SELECT contract_month, base_month, value, provisional
            FROM ecos_mortgage_rate
            WHERE contract_month <= ?
            ORDER BY contract_month DESC
            LIMIT 1
        """

        try:
            with sqlite3.connect(self.path) as connection:
                row = connection.execute(
                    query,
                    (contract_month,),
                ).fetchone()
        except sqlite3.Error as exc:
            raise EcosStoreError("ECOS 조회 실패") from exc

        if row is None:
            return None

        return EcosValue(
            contract_month=row[0],
            base_month=row[1],
            value=row[2],
            provisional=bool(row[3]),
        )

    def _validate(self) -> None:
        if not self.path.is_file():
            raise EcosStoreError(f"ECOS DB 없음: {self.path}")

        try:
            with sqlite3.connect(self.path) as connection:
                version = connection.execute(
                    "SELECT value FROM metadata WHERE key = 'version'"
                ).fetchone()
                count = connection.execute(
                    "SELECT COUNT(*) FROM ecos_mortgage_rate"
                ).fetchone()
        except sqlite3.Error as exc:
            raise EcosStoreError("ECOS DB 읽기 실패") from exc

        if version != ("ecos-v1",):
            raise EcosStoreError("ECOS DB 버전 오류")

        if not count or count[0] <= 0:
            raise EcosStoreError("ECOS 데이터 없음")
