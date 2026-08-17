import sqlite3
from pathlib import Path

from app.diagnosis.property_matcher import (
    PropertyMatcher,
    PropertyReference,
)
from app.diagnosis.schemas import HousingType


class PropertyReferenceStoreError(ValueError):
    pass


class SqlitePropertyReferenceStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        validate_property_reference(self.path)

    def find_parcel(
        self,
        district: str,
        bun: str,
        ji: str,
        housing_type: HousingType,
    ) -> list[PropertyReference]:
        return self._find(
            """
            WHERE district = ? AND bun = ? AND ji = ?
              AND housing_type = ?
            """,
            (district, bun, ji, housing_type.value),
        )

    def find_district(
        self,
        district: str,
        housing_type: HousingType,
    ) -> list[PropertyReference]:
        return self._find(
            "WHERE district = ? AND housing_type = ?",
            (district, housing_type.value),
        )

    def find_type(
        self,
        housing_type: HousingType,
    ) -> list[PropertyReference]:
        return self._find(
            "WHERE housing_type = ?",
            (housing_type.value,),
        )

    def _find(
        self,
        where: str,
        parameters: tuple[str, ...],
    ) -> list[PropertyReference]:
        query = f"""
            SELECT district, bun, ji, housing_type,
                   model_name, source_building_name, sample_count
            FROM property_reference
            {where}
        """

        try:
            with sqlite3.connect(self.path) as connection:
                rows = connection.execute(query, parameters).fetchall()
        except sqlite3.Error as exc:
            raise PropertyReferenceStoreError(
                "Property Reference 조회 실패"
            ) from exc

        return [_to_reference(row) for row in rows]


def validate_property_reference(path: str | Path) -> None:
    database = Path(path)

    if not database.is_file():
        raise PropertyReferenceStoreError(
            f"Property Reference DB 없음: {database}"
        )

    try:
        with sqlite3.connect(database) as connection:
            version = connection.execute(
                "SELECT value FROM metadata WHERE key = 'version'"
            ).fetchone()
            count = connection.execute(
                "SELECT COUNT(*) FROM property_reference"
            ).fetchone()
    except sqlite3.Error as exc:
        raise PropertyReferenceStoreError(
            "Property Reference DB 읽기 실패"
        ) from exc

    if version != ("property-reference-v2",):
        raise PropertyReferenceStoreError(
            "Property Reference DB 버전 오류"
        )

    if not count or count[0] <= 0:
        raise PropertyReferenceStoreError(
            "Property Reference 데이터 없음"
        )


def _to_reference(row: tuple[object, ...]) -> PropertyReference:
    try:
        return PropertyReference(
            district=str(row[0]),
            bun=str(row[1]),
            ji=str(row[2]),
            housing_type=HousingType(str(row[3])),
            model_name=str(row[4]),
            source_building_name=str(row[5]),
            sample_count=int(row[6]),
        )
    except (TypeError, ValueError) as exc:
        raise PropertyReferenceStoreError(
            "Property Reference 레코드 오류"
        ) from exc


def load_property_matcher(path: str | Path) -> PropertyMatcher:
    return PropertyMatcher(SqlitePropertyReferenceStore(path))
