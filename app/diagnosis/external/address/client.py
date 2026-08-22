import requests

from app.diagnosis.external.address.schemas import (
    AddressSearchResult,
)

class AddressApiError(RuntimeError):
    pass

class AddressClient:
    URL = (
        "https://business.juso.go.kr/"
        "addrlink/addrLinkApi.do"
    )
    def __init__(
        self,
        confirmation_key: str,
        timeout: float = 10.0,
        session: requests.Session | None = None,
    ) -> None:
        if not confirmation_key:
            raise ValueError("주소 API 승인키 누락")

        self.confirmation_key = (
            confirmation_key.strip()
        )
        self.timeout = timeout
        self.session = session or requests.Session()

    def search(
        self,
        keyword: str,
        count_per_page: int = 100,
    ) -> AddressSearchResult:
        keyword = keyword.strip()

        if len(keyword) < 2:
            raise ValueError("주소 검색어 길이 부족")
        if not 1 <= count_per_page <= 100:
            raise ValueError("주소 검색 결과 수 범위 오류")

        params = {
            "confmKey": self.confirmation_key,
            "currentPage": "1",
            "countPerPage": str(count_per_page),
            "keyword": keyword,
            "resultType": "json",
            "hstryYn": "Y",
            "firstSort": "none",
            "addInfoYn": "Y",
        }

        try:
            response = self.session.get(
                self.URL,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            status = (
                exc.response.status_code
                if exc.response is not None
                else "연결 오류"
            )

            raise AddressApiError(
                f"주소 API 호출 실패: {status}"
            ) from None
        except ValueError:
            raise AddressApiError(
                "주소 API JSON 변환 실패"
            ) from None

        return self._result(payload)

    @staticmethod
    def _result(
        payload: dict,
    ) -> AddressSearchResult:
        results = payload.get("results", {})
        common = results.get("common", {})

        error_code = str(
            common.get("errorCode", "")
        )

        if error_code != "0":
            message = common.get(
                "errorMessage",
                "알 수 없는 오류",
            )
            raise AddressApiError(
                f"주소 API 오류: {message}"
            )

        raw_items = results.get("juso") or []

        if isinstance(raw_items, dict):
            raw_items = [raw_items]

        if not isinstance(raw_items, list):
            raise AddressApiError(
                "주소 API 응답 형식 오류"
            )

        try:
            total_count = int(
                common.get("totalCount", 0)
            )
        except (TypeError, ValueError):
            raise AddressApiError(
                "주소 API 전체 건수 형식 오류"
            ) from None

        return AddressSearchResult(
            total_count=total_count,
            items=tuple(raw_items),
        )