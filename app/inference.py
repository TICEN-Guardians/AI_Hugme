"""로드된 모델로 회귀 예측을 수행한다."""
from typing import List
import numpy as np


def predict_one(model, features: List[float]) -> float:
    X = np.asarray(features, dtype=float).reshape(1, -1)
    y = model.predict(X)
    return float(np.ravel(y)[0])


def predict_batch(model, instances: List[List[float]]) -> List[float]:
    X = np.asarray(instances, dtype=float)
    y = model.predict(X)
    return [float(v) for v in np.ravel(y)]
