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


@dataclass(frozen=True)
class Settings:
    project_root: Path = PROJECT_ROOT
    upload_dir: Path = Path(os.getenv("UPLOAD_DIR", PROJECT_ROOT / "data" / "uploads"))
    vector_db_dir: Path = Path(os.getenv("CHROMA_DB_DIR", PROJECT_ROOT / "data" / "vector_db"))
    database_url: str = os.getenv("DATABASE_URL", DEFAULT_SQLITE_URL)
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-change-me")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
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


settings = Settings()
