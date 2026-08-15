from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    aws_region: str = "ap-northeast-2"
    s3_bucket: str = ""
    s3_model_key: str = "models/latest/model.pkl"
    model_local_path: str = "/tmp/model.pkl"
    force_download: bool = False

    building_ledger_api_key: str = ""
    building_ledger_api_timeout: float = 10.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
