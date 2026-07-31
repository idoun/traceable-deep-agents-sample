from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="TECH_RADAR_", extra="ignore", populate_by_name=True)

    agent_id: str = "tech-radar"
    agent_name: str = "Tech Radar Analyst"
    data_path: Path = Path("data/sample_articles.jsonl")
    trace_dir: Path = Path(".runtime/traces")
    knowledge_backend: str = "fixture"
    technews_api_base_url: str = Field(default="http://127.0.0.1:8010", validation_alias="TECHNEWS_API_BASE_URL")
    technews_request_timeout: float = Field(default=10.0, validation_alias="TECHNEWS_REQUEST_TIMEOUT")
    technews_auth_token: str = Field(default="", validation_alias="TECHNEWS_AUTH_TOKEN")
    technews_session_cookie: str = Field(default="", validation_alias="TECHNEWS_SESSION_COOKIE")
    model: str = "openai:gpt-5.5"
