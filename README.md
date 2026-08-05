# Regression Inference API

Colab에서 학습한 지도학습 회귀모델을 S3에 저장하고, EC2 위 FastAPI에서 불러와 예측하는 서비스.

## 구조
```
fastapi-inference/
├── app/
│   ├── main.py          # FastAPI 엔드포인트 (/health, /predict, /predict/batch)
│   ├── config.py        # 환경변수 설정
│   ├── model_loader.py  # S3에서 모델 다운로드 + 로드
│   ├── inference.py     # 예측 로직
│   └── schemas.py       # 요청/응답 스키마
├── scripts/
│   ├── colab_upload.py     # 코랩에서 S3 업로드
│   └── make_dummy_model.py # 로컬 테스트용 더미 모델
├── deploy/              # systemd, nginx, IAM 정책
├── Dockerfile
├── requirements.txt
├── .env.example
└── DEPLOY.md            # EC2 배포 가이드
```

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
