import sqlite3
from dataclasses import dataclass
from pathlib import Path


class KosisStoreError(ValueError):
    pass


@dataclass(frozen=True)
class KosisValue:
    contract_month: str
    base_month: str
    feature_name: str
    value: float
    provisional: bool


class KosisStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._validate()

    def find_latest(self, contract_month: str) -> list[KosisValue]:
        query = """
            SELECT contract_month, base_month,
                   feature_name, value, provisional
            FROM kosis_value
            WHERE contract_month = (
                SELECT MAX(contract_month)
                FROM kosis_value
                WHERE contract_month <= ?
            )
            ORDER BY feature_name
        """

        try:
            with sqlite3.connect(self.path) as connection:
                rows = connection.execute(
                    query,
                    (contract_month,),
                ).fetchall()
        except sqlite3.Error as exc:
            raise KosisStoreError("KOSIS 조회 실패") from exc

        return [
            KosisValue(
                contract_month=row[0],
                base_month=row[1],
                feature_name=row[2],
                value=row[3],
                provisional=bool(row[4]),
            )
            for row in rows
        ]

    def _validate(self) -> None:
        if not self.path.is_file():
            raise KosisStoreError(f"KOSIS DB 없음: {self.path}")

        try:
            with sqlite3.connect(self.path) as connection:
                version = connection.execute(
                    "SELECT value FROM metadata WHERE key = 'version'"
                ).fetchone()
                count = connection.execute(
                    "SELECT COUNT(*) FROM kosis_value"
                ).fetchone()
        except sqlite3.Error as exc:
            raise KosisStoreError("KOSIS DB 읽기 실패") from exc

        if version != ("kosis-v1",):
            raise KosisStoreError("KOSIS DB 버전 오류")

        if not count or count[0] <= 0:
            raise KosisStoreError("KOSIS 데이터 없음")
