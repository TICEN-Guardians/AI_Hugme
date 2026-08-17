import argparse
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from psycopg2.extras import execute_values

from app.diagnosis.market_database import get_market_connection


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path("deploy/postgres/property_reference_schema.sql"),
    )
    return parser.parse_args()


def read_source(source: Path) -> tuple[str, list[tuple]]:
    if not source.is_file():
        raise FileNotFoundError(f"Property Reference DB 없음: {source}")

    with sqlite3.connect(source) as connection:
        version = connection.execute(
            "SELECT value FROM metadata WHERE key = 'version'"
        ).fetchone()
        rows = connection.execute(
            """
            SELECT district, bun, ji, housing_type,
                   model_name, source_building_name, sample_count
            FROM property_reference
            """
        ).fetchall()

    if version != ("property-reference-v2",):
        raise ValueError("Property Reference 버전 오류")

    if not rows or any(len(row) != 7 for row in rows):
        raise ValueError("Property Reference 행 오류")

    return version[0], rows


def main() -> None:
    args = parse_args()

    if args.env_file:
        load_dotenv(args.env_file, override=False)

    if not args.schema.is_file():
        raise FileNotFoundError(f"Schema 없음: {args.schema}")

    version, rows = read_source(args.source)
    connection = get_market_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(args.schema.read_text(encoding="utf-8"))
            cursor.execute("TRUNCATE TABLE ai_property_reference")
            execute_values(
                cursor,
                "INSERT INTO ai_property_reference VALUES %s",
                rows,
                page_size=5000,
            )
            cursor.execute(
                """
                INSERT INTO ai_reference_metadata (
                    source_name, version, row_count, loaded_at
                ) VALUES ('property_reference', %s, %s, NOW())
                ON CONFLICT (source_name) DO UPDATE SET
                    version = EXCLUDED.version,
                    row_count = EXCLUDED.row_count,
                    loaded_at = EXCLUDED.loaded_at
                """,
                (version, len(rows)),
            )

        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    print("Property Reference PostgreSQL 적재 완료")
    print(f"- version: {version}")
    print(f"- rows: {len(rows)}")


if __name__ == "__main__":
    main()
