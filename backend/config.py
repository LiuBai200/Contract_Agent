import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")
DEFAULT_SQLITE_URL = f"sqlite:///{(PROJECT_ROOT / 'data' / 'app.db').as_posix()}"


def _first_env(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    project_root: Path = PROJECT_ROOT
    upload_dir: Path = Path(os.getenv("UPLOAD_DIR", PROJECT_ROOT / "data" / "uploads"))
    vector_db_dir: Path = Path(os.getenv("CHROMA_DB_DIR", PROJECT_ROOT / "data" / "vector_db"))
    database_url: str = os.getenv("DATABASE_URL", DEFAULT_SQLITE_URL)
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-change-me")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    rate_limit_enabled: bool = _env_bool("RATE_LIMIT_ENABLED", True)
    rate_limit_fail_open: bool = _env_bool("RATE_LIMIT_FAIL_OPEN", True)
    ask_rate_limit: int = int(os.getenv("ASK_RATE_LIMIT", "10"))
    ask_rate_limit_window_seconds: int = int(os.getenv("ASK_RATE_LIMIT_WINDOW_SECONDS", "60"))
    upload_rate_limit: int = int(os.getenv("UPLOAD_RATE_LIMIT", "5"))
    upload_rate_limit_window_seconds: int = int(os.getenv("UPLOAD_RATE_LIMIT_WINDOW_SECONDS", "60"))
    rag_hits_cache_enabled: bool = _env_bool("RAG_HITS_CACHE_ENABLED", True)
    rag_hits_cache_ttl_seconds: int = int(os.getenv("RAG_HITS_CACHE_TTL_SECONDS", "600"))
    qwen_api_key: str | None = _first_env(
        "DASHSCOPE_API_KEY",
        "ALIYUN_ACCESS_KEY_SECRET",
        "QWEN_API_KEY",
        "OPENAI_API_KEY",
    )
    qwen_base_url: str = os.getenv(
        "QWEN_BASE_URL",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    qwen_model: str = os.getenv("QWEN_MODEL", os.getenv("CHAT_MODEL_NAME", "qwen-plus"))
    qwen_embedding_model: str = os.getenv("QWEN_EMBEDDING_MODEL", "text-embedding-v4")
    chroma_collection: str = os.getenv("CHROMA_COLLECTION", "contract_chunks")
    rerank_enabled: bool = _env_bool("RERANK_ENABLED", True)
    dashscope_base_url: str = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com")
    dashscope_rerank_model: str = os.getenv(
        "DASHSCOPE_RERANK_MODEL",
        os.getenv("QWEN_RERANK_MODEL", "qwen3-rerank"),
    )
    rerank_candidate_k: int = int(os.getenv("RERANK_CANDIDATE_K", "20"))
    rerank_timeout_seconds: int = int(os.getenv("RERANK_TIMEOUT_SECONDS", "60"))
    rerank_instruct: str = os.getenv(
        "DASHSCOPE_RERANK_INSTRUCT",
        "Given a contract review question, retrieve contract clauses that directly answer the question or provide evidence for risk analysis.",
    )


settings = Settings()
