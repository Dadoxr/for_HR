from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = ""

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    # OpenRouter
    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-4o-mini"

    # LLM Router
    llm_provider_order: list[str] = ["openai", "anthropic", "openrouter"]
    llm_timeout: float = 30.0
    llm_max_retries: int = 2

    # RAG
    chunk_size: int = 512
    chunk_overlap: int = 64
    top_k: int = 5

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
