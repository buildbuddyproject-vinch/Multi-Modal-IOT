"""Central configuration, loaded once from .env (falls back to .env.example defaults)."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(PROJECT_ROOT / ".env"), extra="ignore")

    # Dataset paths
    physionet_raw_path: str = "./physionet/challenge-2019-1.0.0/training"
    mimic_iv_raw_path: str = "./mimic-iv-clinical-database-demo-2.2"
    processed_data_path: str = "./data/processed"

    # MongoDB
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db_name: str = "sepsis_icu"

    # MQTT
    mqtt_broker_host: str = "localhost"
    mqtt_broker_port: int = 1883
    mqtt_username: str = ""
    mqtt_password: str = ""

    # Alerting
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    alert_email_from: str = ""
    alert_email_to: str = ""

    # API
    api_secret_key: str = "change_me_in_production"
    log_level: str = "INFO"

    # Alert module (Step 10)
    alert_trigger_risk_levels: str = "High,Critical"
    alert_cooldown_minutes: int = 30

    @property
    def alert_trigger_risk_levels_list(self) -> list[str]:
        return [level.strip() for level in self.alert_trigger_risk_levels.split(",") if level.strip()]

    def resolve_path(self, value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()

    @property
    def physionet_dir(self) -> Path:
        return self.resolve_path(self.physionet_raw_path)

    @property
    def mimic_iv_dir(self) -> Path:
        return self.resolve_path(self.mimic_iv_raw_path)

    @property
    def processed_dir(self) -> Path:
        return self.resolve_path(self.processed_data_path)


@lru_cache
def get_settings() -> Settings:
    return Settings()
