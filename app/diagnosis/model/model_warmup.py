import logging
import os
from threading import Thread

from app.diagnosis.feature_contract import load_feature_contract
from app.diagnosis.model.model_config import load_model_config
from app.diagnosis.model.s3_model_store import S3ModelStore


logger = logging.getLogger(__name__)

THREAD_NAME = "diagnosis-model-prefetch"


def prefetch_enabled() -> bool:
    return os.getenv(
        "DIAGNOSIS_MODEL_PREFETCH",
        "true",
    ).strip().lower() == "true"


def prefetch_model_files() -> None:
    contract = load_feature_contract()
    store = S3ModelStore(load_model_config())
    manifest = store.load_manifest(set(contract.models))
    model_keys = sorted(manifest.models)

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
            logger.exception(
                "진단 모델 사전 다운로드 실패: %s",
                model_key,
            )

    logger.info("진단 모델 사전 다운로드 종료")


def start_model_prefetch() -> None:
    if not prefetch_enabled():
        logger.info("진단 모델 사전 다운로드 비활성화")
        return

    Thread(
        target=_run,
        name=THREAD_NAME,
        daemon=True,
    ).start()


def _run() -> None:
    try:
        prefetch_model_files()
    except Exception:
        logger.exception("진단 모델 사전 다운로드 초기화 실패")
