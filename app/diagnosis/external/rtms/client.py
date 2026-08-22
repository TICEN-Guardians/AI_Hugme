import math
import time
from collections.abc import Mapping
from datetime import date
from functools import lru_cache
from urllib.parse import unquote
from xml.etree import ElementTree

import requests

from app.diagnosis.external.rtms.schemas import RentTransaction
from app.diagnosis.schemas import HousingType


class RtmsApiError(RuntimeError):
    pass


class RtmsClient:
    BASE_URL = "https://apis.data.go.kr/1613000"
    ENDPOINTS = {
        HousingType.APARTMENT: (
            "RTMSDataSvcAptRent/getRTMSDataSvcAptRent"
        ),
        HousingType.VILLA: (
            "RTMSDataSvcRHRent/getRTMSDataSvcRHRent"
        ),
        HousingType.OFFICETEL: (
            "RTMSDataSvcOffiRent/getRTMSDataSvcOffiRent"
        ),
        HousingType.DETACHED_MULTI: (
            "RTMSDataSvcSHRent/getRTMSDataSvcSHRent"
        ),
    }
    PAGE_SIZE = 1000
    MAX_PAGES = 20
    MAX_ATTEMPTS = 3
    RETRY_BACKOFF_SECONDS = 0.5

    def __init__(
        self,
        service_keys: Mapping[HousingType, str],
        timeout: float = 10.0,
        session: requests.Session | None = None,
    ) -> None:
        self.service_keys = {
            housing_type: unquote(service_key.strip())
            for housing_type, service_key in service_keys.items()
            if service_key and service_key.strip()
        }
        if not self.service_keys:
            raise ValueError("국토부 실거래가 API 키 누락")
        self.timeout = timeout
        self.session = session or requests.Session()

    @lru_cache(maxsize=512)
    def get_rent_transactions(
        self,
        housing_type: HousingType,
        district_code: str,
        deal_ym: str,
    ) -> tuple[RentTransaction, ...]:
        if not district_code.isdigit() or len(district_code) != 5:
            raise ValueError("시군구 코드 형식 오류")
        if not deal_ym.isdigit() or len(deal_ym) != 6:
            raise ValueError("계약년월 형식 오류")

        first_root = self._request(
            housing_type=housing_type,
            district_code=district_code,
            deal_ym=deal_ym,
            page_no=1,
        )
        total_count = self._integer(
            self._root_text(first_root, "totalCount")
        )
        pages = min(
            self.MAX_PAGES,
            max(1, math.ceil(total_count / self.PAGE_SIZE)),
        )
        transactions = list(
            self._transactions(first_root)
        )

        for page_no in range(2, pages + 1):
            root = self._request(
                housing_type=housing_type,
                district_code=district_code,
                deal_ym=deal_ym,
                page_no=page_no,
            )
            transactions.extend(self._transactions(root))

        return tuple(transactions)

    def _request(
        self,
        housing_type: HousingType,
        district_code: str,
        deal_ym: str,
        page_no: int,
    ) -> ElementTree.Element:
        endpoint = self.ENDPOINTS[housing_type]
        service_key = self.service_keys.get(housing_type)
        if not service_key:
            raise RtmsApiError(
                f"국토부 실거래가 API 키 누락: {housing_type.value}"
            )
        params = {
            "serviceKey": service_key,
            "LAWD_CD": district_code,
            "DEAL_YMD": deal_ym,
            "pageNo": str(page_no),
            "numOfRows": str(self.PAGE_SIZE),
        }
        error: Exception | None = None

        for attempt in range(self.MAX_ATTEMPTS):
            try:
                response = self.session.get(
                    f"{self.BASE_URL}/{endpoint}",
                    params=params,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                root = ElementTree.fromstring(response.content)
                self._validate(root)
                return root
            except requests.HTTPError as exc:
                error = exc
                if exc.response.status_code not in {
                    429,
                    500,
                    502,
                    503,
                    504,
                }:
                    break
            except (
                requests.ConnectionError,
                requests.Timeout,
                ElementTree.ParseError,
            ) as exc:
                error = exc
            except ValueError as exc:
                error = exc
                break

            if attempt + 1 < self.MAX_ATTEMPTS:
                time.sleep(
                    self.RETRY_BACKOFF_SECONDS * (2 ** attempt)
                )

        status = (
            error.response.status_code
            if isinstance(error, requests.RequestException)
            and error.response is not None
            else "연결 오류"
        )
        raise RtmsApiError(
            f"국토부 실거래가 API 호출 실패: "
            f"{housing_type.value}, {deal_ym}, {status}"
        ) from None

    @classmethod
    def _validate(
        cls,
        root: ElementTree.Element,
    ) -> None:
        auth_message = cls._root_text(
            root,
            "returnAuthMsg",
        )
        result_code = (
            cls._root_text(root, "resultCode")
            or cls._root_text(root, "returnReasonCode")
        )
        if not result_code and not auth_message:
            return
        if result_code in {"00", "000", "0"} and not auth_message:
            return
        result_message = (
            cls._root_text(root, "resultMsg")
            or auth_message
            or "알 수 없는 오류"
        )
        raise ValueError(
            f"국토부 실거래가 API 오류: {result_message}"
        )

    @classmethod
    def _transactions(
        cls,
        root: ElementTree.Element,
    ) -> tuple[RentTransaction, ...]:
        transactions: list[RentTransaction] = []

        for item in root.findall(".//item"):
            if cls._text(item, "cdealDay"):
                continue
            monthly_rent = cls._integer(
                cls._first_text(
                    item,
                    "monthlyRent",
                    "monthlyRentAmount",
                )
            )
            if monthly_rent != 0:
                continue

            deposit = cls._integer(
                cls._first_text(
                    item,
                    "deposit",
                    "depositAmount",
                )
            )
            area = cls._decimal(
                cls._first_text(
                    item,
                    "excluUseAr",
                    "contractArea",
                    "totalFloorAr",
                    "totalFloorArea",
                )
            )
            year = cls._integer(cls._text(item, "dealYear"))
            month = cls._integer(cls._text(item, "dealMonth"))
            day = cls._integer(cls._text(item, "dealDay"))

            if deposit <= 0 or area <= 0:
                continue

            try:
                contract_date = date(year, month, day)
            except ValueError:
                continue

            transactions.append(
                RentTransaction(
                    deposit=deposit * 10_000,
                    area=area,
                    contract_date=contract_date,
                    legal_dong=cls._optional(
                        cls._first_text(
                            item,
                            "umdNm",
                            "legalDong",
                        )
                    ),
                    building_name=cls._optional(
                        cls._first_text(
                            item,
                            "aptNm",
                            "mhouseNm",
                            "offiNm",
                            "buildingName",
                        )
                    ),
                )
            )

        return tuple(transactions)

    @staticmethod
    def _root_text(
        root: ElementTree.Element,
        name: str,
    ) -> str:
        node = root.find(f".//{name}")
        return (node.text or "").strip() if node is not None else ""

    @staticmethod
    def _text(
        item: ElementTree.Element,
        name: str,
    ) -> str:
        node = item.find(name)
        return (node.text or "").strip() if node is not None else ""

    @classmethod
    def _first_text(
        cls,
        item: ElementTree.Element,
        *names: str,
    ) -> str:
        for name in names:
            value = cls._text(item, name)
            if value:
                return value
        return ""

    @staticmethod
    def _integer(value: str) -> int:
        normalized = value.replace(",", "").strip()
        try:
            return int(float(normalized))
        except ValueError:
            return 0

    @staticmethod
    def _decimal(value: str) -> float:
        normalized = value.replace(",", "").strip()
        try:
            return float(normalized)
        except ValueError:
            return 0.0

    @staticmethod
    def _optional(value: str) -> str | None:
        normalized = " ".join(value.split())
        return normalized or None
