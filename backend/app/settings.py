from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application settings loaded from environment variables and the local .env file."""
    app_name: str = "CivicOps AI"
    database_path: str = "./civicops.db"
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-20b"
    use_llm_classifier: bool = False
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
