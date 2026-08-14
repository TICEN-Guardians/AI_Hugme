# Regression Inference API

Colab에서 학습한 지도학습 회귀모델을 S3에 저장하고, EC2 위 FastAPI에서 불러와 예측하는 서비스.


## 로컬 실행
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python scripts/make_dummy_model.py      # /tmp/model.pkl 생성
cp .env.example .env                     # MODEL_LOCAL_PATH=/tmp/model.pkl, S3는 비워도 됨
uvicorn app.main:app --reload
# http://127.0.0.1:8000/docs
```

배포는 `DEPLOY.md` 참고.
