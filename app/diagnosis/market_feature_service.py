from dataclasses import dataclass, replace
from pathlib import Path

from app.diagnosis.external.cofix.service import CofixResult, CofixService
from app.diagnosis.external.cofix.store import CofixStore
from app.diagnosis.external.ecos.service import EcosResult, EcosService
from app.diagnosis.external.ecos.store import EcosStore
from app.diagnosis.external.kosis.service import KosisResult, KosisService
from app.diagnosis.external.kosis.store import KosisStore
from app.diagnosis.external.rone.service import RoneResult, RoneService
from app.diagnosis.external.rone.store import RoneStore
from app.diagnosis.feature_input import FeatureInput
from app.diagnosis.postgres_market_stores import (
    PostgresCofixStore,
    PostgresEcosStore,
    PostgresKosisStore,
    PostgresRoneStore,
)


@dataclass(frozen=True)
class MarketFeatureResult:
    feature_input: FeatureInput
    warnings: tuple[str, ...]
    rone: RoneResult
    cofix: CofixResult
    ecos: EcosResult
    kosis: KosisResult


class MarketFeatureService:
    def __init__(
        self,
        rone_service: RoneService,
        cofix_service: CofixService,
        ecos_service: EcosService,
        kosis_service: KosisService,
    ) -> None:
        self.rone_service = rone_service
        self.cofix_service = cofix_service
        self.ecos_service = ecos_service
        self.kosis_service = kosis_service

    def enrich(
        self,
        model_key: str,
        feature_input: FeatureInput,
    ) -> MarketFeatureResult:
        area = feature_input.property_detail.get("전용면적(㎡)")
        rone = self.rone_service.resolve(
            model_key=model_key,
            district=feature_input.district,
            contract_date=feature_input.contract_date,
            area=float(area) if area is not None else None,
        )
        cofix = self.cofix_service.resolve(feature_input.contract_date)
        ecos = self.ecos_service.resolve(feature_input.contract_date)
        kosis = self.kosis_service.resolve(feature_input.contract_date)
        enriched = replace(
            feature_input,
            rone=dict(rone.values),
            cofix=dict(cofix.values),
            ecos=dict(ecos.values),
            kosis=dict(kosis.values),
        )
        warnings = {
            *rone.warnings,
            *cofix.warnings,
            *ecos.warnings,
            *kosis.warnings,
        }

        return MarketFeatureResult(
            feature_input=enriched,
            warnings=tuple(sorted(warnings)),
            rone=rone,
            cofix=cofix,
            ecos=ecos,
            kosis=kosis,
        )


def load_market_feature_service(
    reference_dir: str | Path,
) -> MarketFeatureService:
    root = Path(reference_dir)

    return MarketFeatureService(
        rone_service=RoneService(RoneStore(root / "rone-v1.sqlite3")),
        cofix_service=CofixService(CofixStore(root / "cofix-v1.sqlite3")),
        ecos_service=EcosService(EcosStore(root / "ecos-v1.sqlite3")),
        kosis_service=KosisService(KosisStore(root / "kosis-v1.sqlite3")),
    )


def load_postgres_market_feature_service() -> MarketFeatureService:
    return MarketFeatureService(
        rone_service=RoneService(PostgresRoneStore()),
        cofix_service=CofixService(PostgresCofixStore()),
        ecos_service=EcosService(PostgresEcosStore()),
        kosis_service=KosisService(PostgresKosisStore()),
    )
