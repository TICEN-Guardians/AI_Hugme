import sqlite3
from dataclasses import dataclass
from pathlib import Path


class RoneStoreError(ValueError):
    pass


@dataclass(frozen=True)
class RoneValue:
    region_path: str
    region_name: str
    base_month: str
    value: float


class RoneStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._validate()

    def find_values(
        self,
        transaction_type: str,
        housing_type: str,
        size_band: str,
        feature_name: str,
        target_month: str,
    ) -> list[RoneValue]:
        query = """
            SELECT region_path, region_name, base_month, value
            FROM rone_value
            WHERE transaction_type = ?
              AND housing_type = ?
              AND size_band = ?
              AND feature_name = ?
              AND base_month <= ?
            ORDER BY base_month DESC
        """
        parameters = (
            transaction_type,
            housing_type,
            size_band,
            feature_name,
            target_month,
        )

        try:
            with sqlite3.connect(self.path) as connection:
                rows = connection.execute(query, parameters).fetchall()
        except sqlite3.Error as exc:
            raise RoneStoreError("RONE 조회 실패") from exc

        return [RoneValue(*row) for row in rows]

    def find_region_path(self, region_name: str) -> tuple[str, ...]:
        query = """
            SELECT region_path
            FROM rone_value
            WHERE region_name = ?
            ORDER BY LENGTH(region_path) DESC
            LIMIT 1
        """

        try:
            with sqlite3.connect(self.path) as connection:
                row = connection.execute(
                    query,
                    (region_name,),
                ).fetchone()
        except sqlite3.Error as exc:
            raise RoneStoreError("RONE 지역 조회 실패") from exc

        return tuple(row[0].split(" > ")) if row else ()

    def _validate(self) -> None:
        if not self.path.is_file():
            raise RoneStoreError(f"RONE DB 없음: {self.path}")

        try:
            with sqlite3.connect(self.path) as connection:
                version = connection.execute(
                    "SELECT value FROM metadata WHERE key = 'version'"
                ).fetchone()
                count = connection.execute(
                    "SELECT COUNT(*) FROM rone_value"
                ).fetchone()
        except sqlite3.Error as exc:
            raise RoneStoreError("RONE DB 읽기 실패") from exc

        if version != ("rone-v1",):
            raise RoneStoreError("RONE DB 버전 오류")

        if not count or count[0] <= 0:
            raise RoneStoreError("RONE 데이터 없음")
