"""
crawl_bad_landlord.py가 만든 CSV를 bad_landlord 테이블에 적재.

실행 : python scripts/load_bad_landlord_to_db.py

"""
import csv
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg2
from psycopg2.extras import execute_values

from app.ocr.address_utils import extract_sigungu
from app.ocr.db import DB_CONFIG

CSV_PATH = Path(
    os.environ.get(
        "BAD_LANDLORD_CSV_PATH",
        str(Path(tempfile.gettempdir()) / "hug_defaulters.csv"),
    )
)


def clean_int(value) -> int | None:
    """'476,000,000' 같은 콤마 섞인 숫자 문자열 -> int.
    빈 값(법인 임대인 등)이면 None."""
    if value is None:
        return None
    digits = re.sub(r"[^\d]", "", str(value))
    if not digits:
        return None
    return int(digits)


def clean_date(value: str) -> str | None:
    if not value or not value.strip():
        return None
    try:
        datetime.strptime(value.strip(), "%Y-%m-%d")
        return value.strip()
    except ValueError:
        return None


def load_rows(csv_path: Path) -> list[tuple]:
    rows = []
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            address = row["address"]
            sigungu = extract_sigungu(address)

            rows.append((
                row["name"],
                clean_int(row["age"]),
                address,
                sigungu,
                clean_int(row["return_debt_amount"]),
                clean_int(row["default_days"]),
                clean_int(row["enforcement_count"]),
                clean_date(row["posted_date"]),
            ))
    return rows


def main():
    if not CSV_PATH.exists():
        raise SystemExit(
            f"{CSV_PATH} 가 없습니다. 먼저 scripts/crawl_bad_landlord.py를 실행해서 "
            f"CSV를 레포 루트에 만들어주세요."
        )

    rows = load_rows(CSV_PATH)
    print(f"{len(rows)}건 읽음")

    missing_sigungu = sum(1 for r in rows if r[3] is None)
    if missing_sigungu:
        print(f"주의: 시군구 정규화 실패(또는 주소 결측) {missing_sigungu}건")

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            # 전체 교체 방식
            cur.execute("TRUNCATE TABLE bad_landlord;")
            execute_values(
                cur,
                """
                INSERT INTO bad_landlord
                    (name, age, address, address_sigungu,
                     return_debt_amount, default_days, enforcement_count, posted_date)
                VALUES %s
                """,
                rows,
            )
        conn.commit()
        print(f"{len(rows)}건 적재 완료")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
