# EC2 배포 가이드 (회귀모델 추론 FastAPI)

## 0. 아키텍처
```
[Colab 학습] --upload--> [S3: models/latest/model.pkl]
                                   |
                            (앱 시작 시 1회 다운로드)
                                   v
        [EC2] Nginx(80) -> Uvicorn(8000) -> FastAPI -> 모델 예측
```

## 1. AWS 준비
1. S3 버킷 생성 (예: `your-bucket-name`), 리전은 EC2와 동일하게 (예: ap-northeast-2).
2. IAM Role 생성 → `deploy/iam-policy.json` 정책 연결 → **EC2 인스턴스에 이 Role을 부여**.
   - 이렇게 하면 서버 코드에 AWS 키를 넣지 않아도 됨 (권장).
3. 보안그룹: 인바운드 22(SSH, 내 IP만), 80(HTTP) 허용.

## 2. EC2에서 실행 — 방법 A: systemd (간단)
```bash
# Ubuntu 22.04/24.04 기준
sudo apt update && sudo apt install -y python3-venv nginx
git clone <레포> fastapi-inference   # 또는 scp로 파일 업로드
cd fastapi-inference
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env    # S3_BUCKET, S3_MODEL_KEY, AWS_REGION 수정
                        # IAM Role 쓰면 AWS 키는 안 넣어도 됨

# systemd 등록
sudo cp deploy/inference-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now inference-api
sudo systemctl status inference-api

# nginx 리버스 프록시
sudo cp deploy/nginx.conf /etc/nginx/sites-available/inference
sudo ln -s /etc/nginx/sites-available/inference /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx
```

## 2. EC2에서 실행 — 방법 B: Docker
```bash
sudo apt update && sudo apt install -y docker.io
sudo docker build -t inference-api .
sudo docker run -d --restart always -p 80:8000 \
  -e S3_BUCKET=your-bucket-name \
  -e S3_MODEL_KEY=models/latest/model.pkl \
  -e AWS_REGION=ap-northeast-2 \
  inference-api
# 주의: Docker에서 IAM Role 자격증명을 쓰려면 EC2 인스턴스 Role이 그대로 상속됨.
```

## 3. 테스트
```bash
curl http://<EC2-퍼블릭-IP>/health
curl -X POST http://<EC2-퍼블릭-IP>/predict \
  -H "Content-Type: application/json" \
  -d '{"features": [0.5, 12.0, 3.2]}'
```
API 문서: `http://<EC2-퍼블릭-IP>/docs`

## 4. 모델 교체 (재배포 없이)
- Colab에서 새 모델을 `models/latest/model.pkl`로 덮어쓰기 업로드.
- 서비스 재시작만 하면 새 모델 로드: `sudo systemctl restart inference-api`
- 무중단이 필요하면 `/reload` 엔드포인트를 추가하거나 blue/green로 확장.

## 주의사항
- **피처 순서**: 예측 요청의 `features` 순서는 학습 시 컬럼 순서와 반드시 동일해야 함.
- **전처리 일관성**: 스케일링/인코딩을 학습에 썼다면 Pipeline으로 묶어 함께 pickle하는 것을 권장.
- **버전 호환**: Colab의 scikit-learn/xgboost 버전과 EC2의 버전을 맞출 것 (requirements.txt 고정 버전 사용).
