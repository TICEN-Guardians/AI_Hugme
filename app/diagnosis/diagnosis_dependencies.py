from functools import lru_cache

from app.config import settings
from app.diagnosis.diagnosis_pipeline import DiagnosisPipeline
from app.diagnosis.external.address.client import AddressClient
from app.diagnosis.external.address.service import AddressService
from app.diagnosis.external.building_ledger.client import BuildingLedgerClient
from app.diagnosis.external.building_ledger.service import BuildingLedgerService
from app.diagnosis.external.rtms.client import RtmsClient
from app.diagnosis.external.rtms.service import (
    MarketComparableService,
)
from app.diagnosis.feature_builder import FeatureBuilder
from app.diagnosis.feature_contract import MANIFEST_PATH, load_feature_contract
from app.diagnosis.feature_fallback import load_feature_fallback_policy
from app.diagnosis.market_feature_service import (
    load_postgres_market_feature_service,
)
from app.diagnosis.model.catboost_adapter import CatBoostAdapter
from app.diagnosis.model.model_config import load_model_config
from app.diagnosis.model.model_predictor import ModelPredictor
from app.diagnosis.model.model_registry import ModelRegistry
from app.diagnosis.model.s3_model_store import S3ModelStore
from app.diagnosis.model.target_transform import TargetTransformer
from app.diagnosis.property_address_service import PropertyAddressService
from app.diagnosis.property_reference_store import (
    load_postgres_property_matcher,
)

from app.diagnosis.schemas import HousingType

@lru_cache(maxsize=1)
def get_diagnosis_pipeline() -> DiagnosisPipeline:
    contract = load_feature_contract()
    defaults_path = MANIFEST_PATH.parent / "feature-defaults.json"
    fallback = load_feature_fallback_policy(
        defaults_path.read_text(encoding="utf-8"),
        contract,
    )
    registry = ModelRegistry(
        contract=contract,
        model_store=S3ModelStore(load_model_config()),
        adapter_factories={"catboost": CatBoostAdapter},
    )
    predictor = ModelPredictor(
        feature_builder=FeatureBuilder(contract, fallback),
        model_registry=registry,
        target_transformer=TargetTransformer(contract),
    )
    address_service = AddressService(
        AddressClient(
            confirmation_key=settings.address_api_confirmation_key,
            timeout=settings.address_api_timeout,
        )
    )
    ledger_service = BuildingLedgerService(
        BuildingLedgerClient(
            service_key=settings.building_ledger_api_key,
            timeout=settings.building_ledger_api_timeout,
        )
    )

    rtms_keys = {
        HousingType.APARTMENT: settings.rtms_apartment_api_key,
        HousingType.VILLA: settings.rtms_villa_api_key,
        HousingType.OFFICETEL: settings.rtms_officetel_api_key,
        HousingType.DETACHED_MULTI: (
            settings.rtms_detached_multi_api_key
        ),
    }
    market_comparable_service = (
        MarketComparableService(
            RtmsClient(rtms_keys, settings.rtms_api_timeout)
        )
        if any(rtms_keys.values())
        else None
    )
    return DiagnosisPipeline(
        property_address_service=PropertyAddressService(
            address_service,
            ledger_service,
        ),
        property_matcher=load_postgres_property_matcher(),
        market_feature_service=load_postgres_market_feature_service(),
        market_comparable_service=market_comparable_service,
        model_predictor=predictor,
    )
