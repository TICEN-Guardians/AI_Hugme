"""
HUG 상습채무불이행자(악성임대인) 명단 크롤러.

크롤링 결과는 load_bad_landloard_to_db.py 에서 수행

실행 : python scripts/crawl_bad_landlord.py
"""
import csv
import os
import re
import tempfile
import time
from pathlib import Path

from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup

load_dotenv()

BASE_URL = "https://www.khug.or.kr/jeonse/web/s01/s010321.jsp"
HEADERS = {"User-Agent": "Mozilla/5.0"}

OUTPUT_CSV = Path(
    os.environ.get(
        "BAD_LANDLORD_CSV_PATH",
        str(Path(tempfile.gettempdir()) / "hug_defaulters.csv"),
    )
)


def fetch_page(page: int) -> str:
    resp = requests.get(BASE_URL, params={"cur_page": page}, headers=HEADERS, timeout=10)
    resp.encoding = "euc-kr"  # 명단 페이지가 EUC-KR 인코딩
    return resp.text


def parse_table(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    rows = []
    for tr in table.find_all("tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(cells) != 10:
            continue
        rows.append({
            "name": cells[0],
            "age": cells[1],
            "address": cells[2],
            "return_debt_amount": cells[3],
            "default_start_date": cells[4],
            "default_days": cells[5],
            "subrogation_date": cells[6],
            "subrogation_amount": cells[7],
            "enforcement_count": cells[8],
            "posted_date": cells[9],
        })
    return rows


def get_total_pages(html: str) -> int:
    text = BeautifulSoup(html, "html.parser").get_text()
    m = re.search(r"(\d+)\s*/\s*(\d+)", text)
    return int(m.group(2)) if m else 1


def crawl_all() -> list[dict]:
    first_html = fetch_page(1)
    total_pages = get_total_pages(first_html)
    print(f"총 {total_pages}페이지")

    all_rows = parse_table(first_html)
    for page in range(2, total_pages + 1):
        all_rows.extend(parse_table(fetch_page(page)))
        time.sleep(0.5)
        if page % 20 == 0:
            print(f"{page}/{total_pages} 진행 중...")
    return all_rows


def main():
    rows = crawl_all()
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)}건 저장 완료 -> {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
