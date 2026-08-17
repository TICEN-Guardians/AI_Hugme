from typing import Any
from urllib.parse import unquote
import requests

from app.diagnosis.external.building_ledger.schemas import (BuildingLedgerKey,)


class BuildingLedgerApiError(RuntimeError):
    pass


class BuildingLedgerClient:
    BASE_URL = (
        "https://apis.data.go.kr/1613000/"
        "BldRgstHubService"
    )

    def __init__(
        self,
        service_key: str,
        timeout: float = 10.0,
        session: requests.Session | None = None,
    ) -> None:
        if not service_key:
            raise ValueError("건축물대장 API 키 누락")

        self.service_key = unquote(service_key.strip())
        self.timeout = timeout
        self.session = session or self._session()

    def get_title(
        self,
        key: BuildingLedgerKey,
    ) -> list[dict[str, Any]]:
        return self._get(
            endpoint="getBrTitleInfo",
            key=key,
        )

    def get_recap_title(
        self,
        key: BuildingLedgerKey,
    ) -> list[dict[str, Any]]:
        return self._get(
            endpoint="getBrRecapTitleInfo",
            key=key,
        )
    def get_exclusive_area(
        self,
        key: BuildingLedgerKey,
        dong_name: str,
        ho_name: str,
    ) -> list[dict[str, Any]]:
        dong = self._suffix(dong_name, "동", False)
        ho = self._suffix(ho_name, "호", True)
        matched: list[dict[str, Any]] = []
        found = False

        for page_no in range(1, 101):
            page = self._get(
                endpoint="getBrExposPubuseAreaInfo",
                key=key,
                extra_params={
                    "dongNm": dong,
                    "hoNm": ho,
                },
                num_of_rows=10,
                page_no=page_no,
            )

            match_indexes = [
                index
                for index, item in enumerate(page)
                if self._same_unit(
                    item.get("dongNm"),
                    item.get("hoNm"),
                    dong,
                    ho,
                )
            ]

            if match_indexes:
                found = True
                matched.extend(
                    page[index]
                    for index in match_indexes
                )

                if match_indexes[-1] < len(page) - 1:
                    return matched
            elif found:
                return matched

            if len(page) < 10:
                return matched

        raise BuildingLedgerApiError(
            "전유공용면적 페이지 범위 초과"
        )

    def _get(
        self,
        endpoint: str,
        key: BuildingLedgerKey,
        extra_params: dict[str, str] | None = None,
        num_of_rows: int = 100,
        page_no: int = 1,
    ) -> list[dict[str, Any]]:
        params = {
            "serviceKey": self.service_key,
            **key.to_params(),
            "numOfRows": str(num_of_rows),
            "pageNo": str(page_no),
            "_type": "json",
        }
        if extra_params:
            params.update(extra_params)

        error: requests.RequestException | ValueError | None = None

        for attempt in range(2):
            try:
                response = self.session.get(
                    f"{self.BASE_URL}/{endpoint}",
                    params=params,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                payload = response.json()
                return self._items(payload)
            except requests.HTTPError as exc:
                error = exc
                status = exc.response.status_code
                if status not in {429, 500, 502, 503, 504}:
                    break
            except (
                requests.ConnectionError,
                requests.Timeout,
                requests.exceptions.JSONDecodeError,
            ) as exc:
                error = exc
            except ValueError as exc:
                error = exc
                break

            if attempt == 1:
                break

        status = (
            error.response.status_code
            if isinstance(error, requests.RequestException)
            and error.response is not None
            else "연결 오류"
        )
        error_name = type(error).__name__

        raise BuildingLedgerApiError(
            f"건축물대장 API 호출 실패: "
            f"{endpoint}, page={page_no}, "
            f"{status}, {error_name}"
        ) from None

    @staticmethod
    def _items(
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        api_response = payload.get("response", {})
        header = api_response.get("header", {})
        result_code = str(
            header.get("resultCode", "")
        )

        if result_code not in {"00", "000", "0"}:
            message = header.get(
                "resultMsg",
                "알 수 없는 오류",
            )
            raise BuildingLedgerApiError(
                f"건축물대장 API 오류: {message}"
            )

        body = api_response.get("body", {})
        items = body.get("items")

        if not items:
            return []

        item = items.get("item", [])

        if isinstance(item, dict):
            return [item]

        if isinstance(item, list):
            return item

        raise BuildingLedgerApiError(
            "건축물대장 응답 형식 오류"
        )
    @staticmethod
    def _suffix(
        value: str,
        suffix: str,
        keep_suffix: bool,
    ) -> str:
        text = "".join(value.split())

        if text.endswith(suffix):
            text = text[:-1]

        if not text:
            raise ValueError(f"{suffix} 정보 누락")

        return text + suffix if keep_suffix else text

    @classmethod
    def _same_unit(
        cls,
        item_dong: Any,
        item_ho: Any,
        dong: str,
        ho: str,
    ) -> bool:
        return (
            cls._unit_value(item_dong, "동")
            == cls._unit_value(dong, "동")
            and cls._unit_value(item_ho, "호")
            == cls._unit_value(ho, "호")
        )

    @staticmethod
    def _unit_value(
        value: Any,
        suffix: str,
    ) -> str:
        text = "".join(str(value or "").split())

        if text.endswith(suffix):
            text = text[:-1]

        return text

    @staticmethod
    def _session() -> requests.Session:
        return requests.Session()
