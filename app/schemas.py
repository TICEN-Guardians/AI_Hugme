from typing import List
from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    """단일 샘플 예측 요청.
    features 순서는 학습 시 사용한 피처 순서와 반드시 일치해야 한다.
    """
    features: List[float] = Field(..., description="입력 피처 벡터", examples=[[0.5, 12.0, 3.2]])


class BatchPredictRequest(BaseModel):
    """여러 샘플 동시 예측."""
    instances: List[List[float]] = Field(..., description="샘플들의 피처 벡터 리스트")


class PredictResponse(BaseModel):
    prediction: float


class BatchPredictResponse(BaseModel):
    predictions: List[float]
