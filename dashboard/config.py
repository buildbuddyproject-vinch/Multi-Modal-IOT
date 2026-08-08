"""Dashboard-side configuration, read from the same .env as the backend
(src/config/settings.py) plus a couple of dashboard-only knobs."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from src.config.settings import PROJECT_ROOT


class DashboardSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(PROJECT_ROOT / ".env"), extra="ignore")

    api_base_url: str = "http://127.0.0.1:8000"
    dashboard_host: str = "127.0.0.1"
    dashboard_port: int = 8050
    dashboard_secret_key: str = "change_me_in_production"
    live_monitoring_poll_seconds: float = 5.0


@lru_cache
def get_dashboard_settings() -> DashboardSettings:
    return DashboardSettings()
