"""S3에서 학습된 회귀 모델 가중치를 받아 메모리로 로드한다."""
import os
import logging

import boto3
import joblib

from app.config import settings

logger = logging.getLogger("model_loader")


def download_from_s3(bucket: str, key: str, local_path: str, force: bool = False) -> str:
    """S3 객체를 local_path로 내려받는다. 이미 있으면 skip(force=True면 재다운로드)."""
    if os.path.exists(local_path) and not force:
        logger.info("모델이 로컬에 이미 있음: %s", local_path)
        return local_path

    os.makedirs(os.path.dirname(local_path) or ".", exist_ok=True)
    # EC2 IAM Role 사용 시 자격증명은 자동으로 주입됨
    s3 = boto3.client("s3", region_name=settings.aws_region)
    logger.info("S3에서 모델 다운로드: s3://%s/%s", bucket, key)
    s3.download_file(bucket, key, local_path)
    return local_path


def load_model():
    """앱 시작 시 한 번 호출. 로드된 모델 객체를 반환한다."""
    path = download_from_s3(
        settings.s3_bucket,
        settings.s3_model_key,
        settings.model_local_path,
        force=settings.force_download,
    )
    model = joblib.load(path)  # sklearn / xgboost(sklearn API) 모두 지원
    logger.info("모델 로드 완료: %s", type(model).__name__)
    return model
