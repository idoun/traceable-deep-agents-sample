from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="TECH_RADAR_", extra="ignore", populate_by_name=True)

    agent_id: str = "tech-radar"
    agent_name: str = "Tech Radar Analyst"
    data_path: Path = Path("data/sample_articles.jsonl")
    trace_dir: Path = Path(".runtime/traces")
    knowledge_backend: str = "fixture"
    server_host: str = "127.0.0.1"
    server_port: int = 8776
    technews_api_base_url: str = Field(default="http://127.0.0.1:8010", validation_alias="TECHNEWS_API_BASE_URL")
    technews_request_timeout: float = Field(default=10.0, validation_alias="TECHNEWS_REQUEST_TIMEOUT")
    technews_auth_token: str = Field(default="", validation_alias="TECHNEWS_AUTH_TOKEN")
    technews_session_cookie: str = Field(default="", validation_alias="TECHNEWS_SESSION_COOKIE")
    # TECH_RADAR_MODEL keeps the original Deep Agents model-string escape hatch.
    # When it is empty, provider-specific settings mirror traceable-agent-runtime.
    model: str = Field(default="", validation_alias="TECH_RADAR_MODEL")
    llm_provider: str = Field(default="openai", validation_alias=AliasChoices("TECH_RADAR_LLM_PROVIDER", "LLM_PROVIDER"))
    llm_model: str = Field(default="gpt-5.5", validation_alias=AliasChoices("TECH_RADAR_LLM_MODEL", "LLM_MODEL"))
    openai_api_key: str = Field(default="", validation_alias=AliasChoices("TECH_RADAR_OPENAI_API_KEY", "OPENAI_API_KEY"))
    openai_base_url: str = Field(default="https://api.openai.com/v1", validation_alias=AliasChoices("TECH_RADAR_OPENAI_BASE_URL", "LLM_BASE_URL"))
    gemini_api_key: str = Field(default="", validation_alias=AliasChoices("TECH_RADAR_GEMINI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"))
    gemini_model: str = Field(default="gemini-2.5-flash", validation_alias=AliasChoices("TECH_RADAR_GEMINI_MODEL", "GEMINI_MODEL"))
    execution_mode: str = Field(default="auto", validation_alias="TECH_RADAR_EXECUTION_MODE")
    deep_path_enabled: bool = Field(default=False, validation_alias="TECH_RADAR_DEEP_PATH_ENABLED")
    app_env: str = Field(default="development", validation_alias=AliasChoices("TECH_RADAR_APP_ENV", "APP_ENV"))
