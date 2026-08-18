import argparse
import sqlite3
from pathlib import Path

from psycopg2.extras import execute_values
from dotenv import load_dotenv

from app.diagnosis.market_database import get_market_connection


SOURCES = {
    "rone": (
        "rone-v1.sqlite3",
        "rone_value",
        "ai_rone_value",
        8,
    ),
    "cofix": (
        "cofix-v1.sqlite3",
        "cofix_value",
        "ai_cofix_value",
        3,
    ),
    "ecos": (
        "ecos-v1.sqlite3",
        "ecos_mortgage_rate",
        "ai_ecos_mortgage_rate",
        4,
    ),
    "kosis": (
        "kosis-v1.sqlite3",
        "kosis_value",
        "ai_kosis_value",
        5,
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-dir", type=Path, required=True)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path("deploy/postgres/market_feature_schema.sql"),
    )
    return parser.parse_args()


def read_source(
    reference_dir: Path,
    file_name: str,
    table_name: str,
    width: int,
) -> tuple[str, list[tuple]]:
    path = reference_dir / file_name

    if not path.is_file():
        raise FileNotFoundError(f"경제지표 DB 없음: {path}")

    with sqlite3.connect(path) as connection:
        version = connection.execute(
            "SELECT value FROM metadata WHERE key = 'version'"
        ).fetchone()
        rows = connection.execute(
            f"SELECT * FROM {table_name}"
        ).fetchall()

    if version is None:
        raise ValueError(f"경제지표 버전 없음: {file_name}")

    if not rows or any(len(row) != width for row in rows):
        raise ValueError(f"경제지표 행 오류: {file_name}")

    if table_name in {"ecos_mortgage_rate", "kosis_value"}:
        rows = [(*row[:-1], bool(row[-1])) for row in rows]

    return version[0], rows


def main() -> None:
    args = parse_args()

    if args.env_file:
        load_dotenv(args.env_file, override=False)

    if not args.schema.is_file():
        raise FileNotFoundError(f"Schema 없음: {args.schema}")

    loaded = {
        name: read_source(
            args.reference_dir,
            file_name,
            sqlite_table,
            width,
        )
        for name, (
            file_name,
            sqlite_table,
            _,
            width,
        ) in SOURCES.items()
    }
    connection = get_market_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(args.schema.read_text(encoding="utf-8"))

            for name, (_, _, postgres_table, _) in SOURCES.items():
                version, rows = loaded[name]
                cursor.execute(f"TRUNCATE TABLE {postgres_table}")
                execute_values(
                    cursor,
                    f"INSERT INTO {postgres_table} VALUES %s",
                    rows,
                    page_size=5000,
                )
                cursor.execute(
                    """
                    INSERT INTO ai_market_metadata (
                        source_name, version, row_count, loaded_at
                    ) VALUES (%s, %s, %s, NOW())
                    ON CONFLICT (source_name) DO UPDATE SET
                        version = EXCLUDED.version,
                        row_count = EXCLUDED.row_count,
                        loaded_at = EXCLUDED.loaded_at
                    """,
                    (name, version, len(rows)),
                )

        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    print("경제·금리 데이터 PostgreSQL 적재 완료")

    for name, (version, rows) in loaded.items():
        print(f"- {name}: version={version}, rows={len(rows)}")


if __name__ == "__main__":
    main()
