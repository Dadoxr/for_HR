from pydantic import BaseModel, Field, model_validator


class IngestRequest(BaseModel):
    title: str = Field(..., description="Document title for identification")
    text: str = Field(..., description="Full text content to chunk, embed, and store")
    source: str = Field("", description="Optional source label (e.g. 'wiki', 'manual')")
    openai_api_key: str | None = Field(None, description="Your OpenAI API key for embeddings. Required if server has no key configured.")


class IngestResponse(BaseModel):
    document_id: str = Field(..., description="UUID of the created document")
    chunks_count: int = Field(..., description="Number of text chunks stored")


class QueryRequest(BaseModel):
    question: str = Field(..., description="Question to answer using RAG pipeline")
    top_k: int | None = Field(None, description="Number of most relevant chunks to retrieve (default: 5)")
    document_id: str | None = Field(None, description="Limit search to a specific document UUID")
    provider: str | None = Field(None, description="LLM provider: openai, anthropic, or openrouter. Required if passing api_key.")
    api_key: str | None = Field(None, description="Your API key for the chosen provider. Overrides server config.")
    model: str | None = Field(None, description="Model name, e.g. gpt-4o-mini, claude-sonnet-4-20250514")
    openai_api_key: str | None = Field(None, description="OpenAI key for embeddings (if different from api_key). Falls back to api_key for openai provider.")

    model_config = {"protected_namespaces": ()}

    @model_validator(mode="after")
    def validate_provider_with_key(self):
        if self.api_key and not self.provider:
            raise ValueError("'provider' is required when 'api_key' is set. Choose: openai, anthropic, or openrouter.")
        return self


class QueryResponse(BaseModel):
    answer: str = Field(..., description="Generated answer based on retrieved context")
    sources: list[str] = Field(..., description="Context chunk references used in the answer")
    confidence: float = Field(..., description="Model's confidence score (0.0 to 1.0)")
    provider_used: str | None = Field(None, description="LLM provider that generated the answer")
    model_used: str | None = Field(None, description="Model that generated the answer")

    model_config = {"protected_namespaces": ()}


class HealthResponse(BaseModel):
    status: str = Field(..., description="Service health status")
    providers: list[dict] = Field(..., description="Configured LLM providers and their status")
