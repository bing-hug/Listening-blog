import warnings
from pydantic_settings import BaseSettings


_INSECURE_DEFAULT = "change-me-in-production"


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://juflow:juflow_dev@localhost:5432/juflow"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = _INSECURE_DEFAULT
    access_token_expire_minutes: int = 1440
    rsshub_url: str = "http://localhost:1200"
    vapid_private_key: str = ""
    vapid_public_key: str = ""
    vapid_claim_email: str = "admin@example.com"
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@juflow.app"
    cors_origins: str = "http://localhost:5173,http://localhost:80"
    # NapCat (QQ 通知) — OneBot v11 HTTP 服务地址与 access_token
    napcat_base_url: str = "http://localhost:3000"
    napcat_access_token: str = ""
    # WeClawBot-API (个人微信通知) — HTTP 服务地址，bot_id / api_token 在用户设置中配置
    weclawbot_base_url: str = "http://localhost:26322"
    # Logging — 统一错误日志写入 {log_dir}/error.log，全量日志 {log_dir}/app.log
    log_dir: str = "logs"
    log_level: str = "INFO"

    model_config = {"env_file": ".env"}


settings = Settings()

if settings.secret_key == _INSECURE_DEFAULT:
    warnings.warn(
        "SECRET_KEY is using the insecure default. Set SECRET_KEY in .env before deploying to production.",
        stacklevel=1,
    )
