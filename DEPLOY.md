# AI 서비스 배포

AI 서비스의 컨테이너 빌드와 실행 환경은 Infra_Hugme의 Docker Compose 설정을 기준으로 관리합니다.

## 필수 모델 설정

- AWS_REGION
- MODEL_S3_BUCKET
- MODEL_MANIFEST_KEY
- MODEL_CACHE_DIR
- DIAGNOSIS_MODEL_PREFETCH
- AWS 실행 자격증명 또는 인스턴스 역할

AWS 실행 주체에는 매니페스트와 매니페스트의 각 s3_key에 대한 s3:GetObject 권한이 필요합니다. Access Key와 Secret은 저장소에 기록하지 않습니다.

## 실행 확인

    docker compose up -d ai
    curl http://localhost:8000/health
    docker compose logs ai

diagnosisModels.prefetchStatus가 READY이고 로그에 8개 모델의 준비 완료가 기록되면 진단 모델을 사용할 수 있습니다.
