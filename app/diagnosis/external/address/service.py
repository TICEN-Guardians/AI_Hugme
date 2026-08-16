from app.diagnosis.external.address.client import (
    AddressClient,
)
from app.diagnosis.external.address.mapper import (
    AddressMapper,
)
from app.diagnosis.external.address.schemas import (
    ResolvedAddress,
)


class AddressResolutionError(ValueError):
    pass


class AddressService:
    def __init__(
        self,
        client: AddressClient,
    ) -> None:
        self.client = client

    def resolve(
        self,
        keyword: str,
    ) -> ResolvedAddress:
        result = self.client.search(keyword)

        if result.total_count == 0:
            raise AddressResolutionError(
                "일치하는 주소 없음"
            )

        if result.total_count != 1:
            raise AddressResolutionError(
                f"주소 검색 결과 다수: "
                f"{result.total_count}건"
            )

        if len(result.items) != 1:
            raise AddressResolutionError(
                "주소 검색 결과 수 불일치"
            )

        return AddressMapper.map_result(
            result.items[0]
        )