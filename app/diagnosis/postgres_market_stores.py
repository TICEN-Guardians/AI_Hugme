from datetime import date

from app.diagnosis.external.cofix.store import CofixValue
from app.diagnosis.external.ecos.store import EcosValue
from app.diagnosis.external.kosis.store import KosisValue
from app.diagnosis.external.rone.store import RoneValue
from app.diagnosis.market_database import get_market_connection


class PostgresRoneStore:
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
            FROM ai_rone_value
            WHERE transaction_type = %s
              AND housing_type = %s
              AND size_band = %s
              AND feature_name = %s
              AND base_month <= %s
            ORDER BY base_month DESC
        """
        rows = self._fetchall(
            query,
            (
                transaction_type,
                housing_type,
                size_band,
                feature_name,
                target_month,
            ),
        )
        return [RoneValue(*row) for row in rows]

    def find_region_path(self, region_name: str) -> tuple[str, ...]:
        query = """
            SELECT region_path
            FROM ai_rone_value
            WHERE region_name = %s
            ORDER BY LENGTH(region_path) DESC
            LIMIT 1
        """
        rows = self._fetchall(query, (region_name,))
        return tuple(rows[0][0].split(" > ")) if rows else ()

    @staticmethod
    def _fetchall(query: str, parameters: tuple) -> list[tuple]:
        connection = get_market_connection()

        try:
            with connection.cursor() as cursor:
                cursor.execute(query, parameters)
                return cursor.fetchall()
        finally:
            connection.close()


class PostgresCofixStore:
    def find_latest(self, contract_date: date) -> CofixValue | None:
        query = """
            SELECT publication_date, target_month, value
            FROM ai_cofix_value
            WHERE publication_date <= %s
            ORDER BY publication_date DESC
            LIMIT 1
        """
        row = _fetchone(query, (contract_date,))

        if row is None:
            return None

        return CofixValue(
            publication_date=row[0],
            target_month=row[1],
            value=row[2],
        )


class PostgresEcosStore:
    def find_latest(self, contract_month: str) -> EcosValue | None:
        query = """
            SELECT contract_month, base_month, value, provisional
            FROM ai_ecos_mortgage_rate
            WHERE contract_month <= %s
            ORDER BY contract_month DESC
            LIMIT 1
        """
        row = _fetchone(query, (contract_month,))

        if row is None:
            return None

        return EcosValue(
            contract_month=row[0],
            base_month=row[1],
            value=row[2],
            provisional=row[3],
        )


class PostgresKosisStore:
    def find_latest(self, contract_month: str) -> list[KosisValue]:
        query = """
            SELECT contract_month, base_month,
                   feature_name, value, provisional
            FROM ai_kosis_value
            WHERE contract_month = (
                SELECT MAX(contract_month)
                FROM ai_kosis_value
                WHERE contract_month <= %s
            )
            ORDER BY feature_name
        """
        rows = _fetchall(query, (contract_month,))
        return [
            KosisValue(
                contract_month=row[0],
                base_month=row[1],
                feature_name=row[2],
                value=row[3],
                provisional=row[4],
            )
            for row in rows
        ]


def _fetchone(query: str, parameters: tuple) -> tuple | None:
    connection = get_market_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(query, parameters)
            return cursor.fetchone()
    finally:
        connection.close()


def _fetchall(query: str, parameters: tuple) -> list[tuple]:
    connection = get_market_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(query, parameters)
            return cursor.fetchall()
    finally:
        connection.close()
