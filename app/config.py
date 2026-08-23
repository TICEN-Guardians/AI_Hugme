from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    building_ledger_api_key: str = ""
    building_ledger_api_timeout: float = 10.0
    rtms_apartment_api_key: str = ""
    rtms_villa_api_key: str = ""
    rtms_officetel_api_key: str = ""
    rtms_detached_multi_api_key: str = ""
    rtms_api_timeout: float = 10.0

    address_api_confirmation_key: str = ""
    address_api_timeout: float = 10.0

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
