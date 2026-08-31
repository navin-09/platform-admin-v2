from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "platform-admin"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"
    database_url: str

    # CORS
    cors_origins: list[str] = ["*"]

    # Logging
    log_level: str = "INFO"
    log_to_console: bool = True
    log_to_file: bool = True
    log_file: str = "logs/app_logs/platform-admin.log"
    log_file_max_bytes: int = 10_000_000
    log_file_backup_count: int = 5

    # Tracing
    tracing_enabled: bool = False
    tracing_service_name: str = "platform-admin"
    tracing_otlp_endpoint: str | None = None
    tracing_sample_rate: float = 1.0
    tracing_log_to_file: bool = True
    tracing_log_file: str = "logs/trace_logs/traces.log"
    tracing_log_to_console: bool = False

    # Auth
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 20
    refresh_token_expire_days: int = 7
    max_failed_login_attempts: int = 5
    lockout_minutes: int = 15
    otp_expiry_minutes: int = 10
    otp_max_requests_per_window: int = 3
    otp_throttle_window_minutes: int = 15
    password_history_depth: int = 3

    # Audit
    audit_retention_days: int = 365

    # Exports (reason, 24h single-user link, max 100k rows/file)
    export_dir: str = "exports"
    export_link_ttl_hours: int = 24
    export_max_rows: int = 100_000
    export_stream_chunk_size: int = 1000

    @property
    def export_dir_path(self) -> Path:
        return Path(self.export_dir)


settings = Settings()
