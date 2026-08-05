"""로컬 테스트용 더미 회귀 모델 생성 -> /tmp/model.pkl"""
import joblib
import numpy as np
from sklearn.linear_model import LinearRegression

X = np.random.rand(100, 3)
y = X @ np.array([2.0, -1.0, 0.5]) + 0.1
model = LinearRegression().fit(X, y)
joblib.dump(model, "/tmp/model.pkl")
print("dummy model saved to /tmp/model.pkl")
