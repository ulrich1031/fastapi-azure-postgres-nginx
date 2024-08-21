import os
from functools import lru_cache
from enum import Enum
from pydantic_settings import BaseSettings


class Environment(Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"


class Settings(BaseSettings):
    # Required settings
    PG_AGENT_DATABASE_URL: str
    PG_MAIN_DATABASE_URL: str

    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_API_KEY: str
    AZURE_OPENAI_API_VERSION: str
    AZURE_OPENAI_DEPLOYMENT_NAME: str
    AZURE_EMBEDDING_MODEL: str
    
    EXA_API_KEY: str
    TAVILY_API_KEY: str
    
    LANGFUSE_SECRET_KEY: str
    LANGFUSE_PUBLIC_KEY: str
    LANGFUSE_HOST: str

    FAST_LLM_MODEL: str
    SMART_LLM_MODEL: str
    
    DOMAIN: str

    # Optional settings
    ENVIRONMENT: str = Environment.PRODUCTION.value
    ORIGINS: list[str] = ["*"]

    DJANGO_SERVER: str
    DJANGO_SERVER_JWT_SECRET_KEY: str


@lru_cache
def get_settings():
    return Settings()
