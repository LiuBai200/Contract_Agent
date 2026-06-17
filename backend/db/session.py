from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.config import settings


class Base(DeclarativeBase):
    pass


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    from backend.db import models  # noqa: F401

    settings.project_root.joinpath("data").mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    _ensure_chat_message_columns()


def _ensure_chat_message_columns() -> None:
    inspector = inspect(engine)
    if "chat_messages" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("chat_messages")}
    if "citations_json" in columns:
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE chat_messages ADD COLUMN citations_json TEXT"))


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
