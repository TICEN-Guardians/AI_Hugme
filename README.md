# AI Hugme

전세 위험도 진단에 필요한 주소·공공데이터 조회, 시세 추정, 등기부 구조화 추출과 위험 규칙 계산을 제공하는 FastAPI 서비스입니다.

## 로컬 실행

전체 로컬 환경은 Infra_Hugme의 Docker Compose로 실행합니다.

    docker compose build ai
    docker compose up -d ai

AI 서비스 단독 실행이 필요하면 환경변수를 준비한 뒤 다음 명령을 사용합니다.

    pip install -r requirements.txt
    uvicorn app.main:app --reload

## 진단 모델

진단 모델은 MODEL_MANIFEST_KEY의 매니페스트를 먼저 검증하고, 매니페스트에 기록된 8개 CatBoost 모델을 MODEL_CACHE_DIR에 저장합니다. 각 모델은 Feature 계약과 SHA-256 검증을 통과해야 로드됩니다.

GET /health 응답의 diagnosisModels.prefetchStatus는 다음 상태 중 하나입니다.

- PENDING: 모델 확인 진행 중
- READY: 전체 모델 준비 완료
- FAILED: 매니페스트 또는 모델 준비 실패
- DISABLED: 사전 다운로드 비활성화

## 검증

    python -m unittest discover -s tests
