import logging
import os
from enum import Enum
from threading import Lock, Thread

from app.diagnosis.feature_contract import load_feature_contract
from app.diagnosis.model.model_config import load_model_config
from app.diagnosis.model.s3_model_store import S3ModelStore


logger = logging.getLogger(__name__)

THREAD_NAME = "diagnosis-model-prefetch"


class ModelPrefetchStatus(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    FAILED = "FAILED"
    DISABLED = "DISABLED"


_model_prefetch_status = ModelPrefetchStatus.PENDING
_model_prefetch_status_lock = Lock()


def get_model_prefetch_status() -> ModelPrefetchStatus:
    with _model_prefetch_status_lock:
        return _model_prefetch_status


def _set_model_prefetch_status(
    status: ModelPrefetchStatus,
) -> None:
    global _model_prefetch_status

    with _model_prefetch_status_lock:
        _model_prefetch_status = status


def prefetch_enabled() -> bool:
    value = os.getenv(
        "DIAGNOSIS_MODEL_PREFETCH",
        "",
    ).strip().lower()

    if not value:
        return True

    return value not in {"false", "0", "no", "off"}


def prefetch_model_files() -> bool:
    contract = load_feature_contract()
    store = S3ModelStore(load_model_config())
    manifest = store.load_manifest(set(contract.models))
    model_keys = sorted(manifest.models)
    all_ready = True

    logger.info(
        "진단 모델 사전 다운로드 시작: %d건 (manifest=%s)",
        len(model_keys),
        manifest.version,
    )

    for model_key in model_keys:
        try:
            store.get_model_path(
                manifest=manifest,
                model_key=model_key,
            )
            logger.info("진단 모델 준비 완료: %s", model_key)
        except Exception:
            all_ready = False
            logger.exception(
                "진단 모델 사전 다운로드 실패: %s",
                model_key,
            )

    logger.info("진단 모델 사전 다운로드 종료")
    return all_ready


def start_model_prefetch() -> None:
    if not prefetch_enabled():
        _set_model_prefetch_status(
            ModelPrefetchStatus.DISABLED
        )
        logger.info("진단 모델 사전 다운로드 비활성화")
        return

    _set_model_prefetch_status(
        ModelPrefetchStatus.PENDING
    )
    Thread(
        target=_run,
        name=THREAD_NAME,
        daemon=True,
    ).start()


def _run() -> None:
    try:
        all_ready = prefetch_model_files()
    except Exception:
        _set_model_prefetch_status(
            ModelPrefetchStatus.FAILED
        )
        logger.exception(
            "진단 모델 사전 다운로드 초기화 실패"
        )
        return

    _set_model_prefetch_status(
        ModelPrefetchStatus.READY
        if all_ready
        else ModelPrefetchStatus.FAILED
    )
