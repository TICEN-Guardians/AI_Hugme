import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path


class CofixStoreError(ValueError):
    pass


@dataclass(frozen=True)
class CofixValue:
    publication_date: date
    target_month: str
    value: float


class CofixStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._validate()

    def find_latest(self, contract_date: date) -> CofixValue | None:
        query = """
            SELECT publication_date, target_month, value
            FROM cofix_value
            WHERE publication_date <= ?
            ORDER BY publication_date DESC
            LIMIT 1
        """

        try:
            with sqlite3.connect(self.path) as connection:
                row = connection.execute(
                    query,
                    (contract_date.isoformat(),),
                ).fetchone()
        except sqlite3.Error as exc:
            raise CofixStoreError("COFIX 조회 실패") from exc

        if row is None:
            return None

        return CofixValue(
            publication_date=date.fromisoformat(row[0]),
            target_month=row[1],
            value=row[2],
        )

    def _validate(self) -> None:
        if not self.path.is_file():
            raise CofixStoreError(f"COFIX DB 없음: {self.path}")

        try:
            with sqlite3.connect(self.path) as connection:
                version = connection.execute(
                    "SELECT value FROM metadata WHERE key = 'version'"
                ).fetchone()
                count = connection.execute(
                    "SELECT COUNT(*) FROM cofix_value"
                ).fetchone()
        except sqlite3.Error as exc:
            raise CofixStoreError("COFIX DB 읽기 실패") from exc

        if version != ("cofix-v1",):
            raise CofixStoreError("COFIX DB 버전 오류")

        if not count or count[0] <= 0:
            raise CofixStoreError("COFIX 데이터 없음")
