"""코랩에서 학습 완료 후 실행: 모델을 pickle로 저장하고 S3에 업로드."""
import joblib
import boto3

# 1) 학습된 모델 저장 (예: model = RandomForestRegressor().fit(X, y))
joblib.dump(model, "model.pkl")  # noqa: F821  (model은 학습 코드에서 정의됨)

# 2) S3 업로드
s3 = boto3.client(
    "s3",
    aws_access_key_id="YOUR_KEY",       # 코랩은 IAM Role이 없으므로 키 사용
    aws_secret_access_key="YOUR_SECRET",
    region_name="ap-northeast-2",
)

BUCKET = "your-bucket-name"
# 버전 관리를 위해 타임스탬프 경로 + latest 둘 다 올리는 패턴 권장
s3.upload_file("model.pkl", BUCKET, "models/2026-08-05/model.pkl")
s3.upload_file("model.pkl", BUCKET, "models/latest/model.pkl")
print("업로드 완료")
