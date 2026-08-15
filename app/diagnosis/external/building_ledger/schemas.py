from dataclasses import dataclass


@dataclass(frozen=True)
class BuildingLedgerKey:
    sigungu_code: str
    bjdong_code: str
    plat_code: str
    bun: str
    ji: str

    def __post_init__(self) -> None:
        fields = {
            "sigungu_code": (self.sigungu_code, 5),
            "bjdong_code": (self.bjdong_code, 5),
            "plat_code": (self.plat_code, 1),
            "bun": (self.bun, 4),
            "ji": (self.ji, 4),
        }

        for name, (value, length) in fields.items():
            if not value.isdigit() or len(value) != length:
                raise ValueError(
                    f"{name} 형식 오류: {value}"
                )

    def to_params(self) -> dict[str, str]:
        return {
            "sigunguCd": self.sigungu_code,
            "bjdongCd": self.bjdong_code,
            "platGbCd": self.plat_code,
            "bun": self.bun,
            "ji": self.ji,
        }