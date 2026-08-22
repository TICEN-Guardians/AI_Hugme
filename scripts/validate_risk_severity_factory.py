from dataclasses import replace
from datetime import date

from app.diagnosis.external.cofix.service import CofixResult
from app.diagnosis.external.ecos.service import EcosResult
from app.diagnosis.external.kosis.service import KosisResult
from app.diagnosis.external.rone.service import RoneResult
from app.diagnosis.feature_input import FeatureInput
from app.diagnosis.market_feature_service import MarketFeatureResult
from app.diagnosis.risk_severity_factory import RiskSeverityFactory


def market(rone_change: float) -> MarketFeatureResult:
    feature_input = FeatureInput(
        contract_date=date(2026, 8, 17),
        normalized_address="테스트 주소",
        district="서울특별시 강남구 개포동",
        housing_type="아파트",
        building_ledger={"사용승인연도": 1991},
    )
    return MarketFeatureResult(
        feature_input=feature_input,
        warnings=(),
        rone=RoneResult(
            values={"RONE_가격지수_전월비": rone_change},
            base_months={},
            regions={},
            warnings=(),
        ),
        cofix=CofixResult(
            values={"신규취급액기준_COFIX": 3.05},
            publication_date=None,
            target_month="2026-06",
            warnings=(),
        ),
        ecos=EcosResult(
            values={"ECOS_주담대금리_적용값": 4.36},
            contract_month="2026-07",
            base_month="2026-06",
            warnings=(),
        ),
        kosis=KosisResult(
            values={
                "KOSIS_건설기성액": -1.3,
                "KOSIS_경제심리지수": -0.4,
                "KOSIS_선행지수_순환변동치": 104.8,
            },
            contract_month="2026-07",
            base_month="2026-05",
            warnings=(),
        ),
    )


def main() -> None:
    sale = market(-1.0)
    lease = replace(
        sale,
        rone=replace(
            sale.rone,
            values={"RONE_가격지수_전월비": -0.5},
        ),
    )
    result = RiskSeverityFactory.create(
        sale_market=sale,
        lease_market=lease,
    )

    assert result.sale_price_change == -1.0
    assert result.lease_price_change == -0.5
    assert result.severity.sale_price_decline == 0.5
    assert result.severity.lease_price_decline == 0.25

    print("시장 추세 심각도 Factory 검증 완료")
    print(f"- 매매 변동: {result.sale_price_change}")
    print(f"- 전세 변동: {result.lease_price_change}")
    print(f"- 심각도: {result.severity}")


if __name__ == "__main__":
    main()
