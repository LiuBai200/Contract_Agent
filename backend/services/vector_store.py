import hashlib
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_core.documents import Document

from backend.config import settings
from backend.services.embedding_service import QwenEmbeddingClient


class VectorStoreService:
    def __init__(self):
        settings.vector_db_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=str(settings.vector_db_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=settings.chroma_collection,
            metadata={"description": "Contract review RAG chunks"},
        )
        self._embedding_client: QwenEmbeddingClient | None = None

    @property
    def embedding_client(self) -> QwenEmbeddingClient:
        if self._embedding_client is None:
            self._embedding_client = QwenEmbeddingClient()
        return self._embedding_client

    async def add_documents(self, chunks: list[Document]) -> int:
        if not chunks:
            return 0

        texts = [chunk.page_content for chunk in chunks]
        metadatas = [_clean_metadata(chunk.metadata) for chunk in chunks]
        ids = [_make_chunk_id(text, metadata, index) for index, (text, metadata) in enumerate(zip(texts, metadatas))]
        embeddings = await self.embedding_client.embed_texts(texts)
        self.collection.upsert(
            ids=ids,
            documents=texts,
            metadatas=metadatas,
            embeddings=embeddings,
        )
        return len(chunks)

    async def search(
        self,
        query: str,
        user_id: int,
        top_k: int = 5,
        contract_id: int | None = None,
    ) -> list[dict[str, Any]]:
        query_embedding = (await self.embedding_client.embed_texts([query]))[0]
        where = {"user_id": str(user_id)}
        if contract_id is not None:
            where = {
                "$and": [
                    {"user_id": str(user_id)},
                    {"contract_id": str(contract_id)},
                ]
            }
        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        hits = []
        for document, metadata, distance in zip(documents, metadatas, distances):
            hits.append(
                {
                    "content": document,
                    "metadata": metadata or {},
                    "distance": distance,
                    "score": round(1 / (1 + distance), 4) if distance is not None else None,
                }
            )
        return hits

    def count(self) -> int:
        return self.collection.count()

    async def delete_contract(self, user_id: int, contract_id: int) -> None:
        self.collection.delete(
            where={
                "$and": [
                    {"user_id": str(user_id)},
                    {"contract_id": str(contract_id)},
                ]
            }
        )


def _make_chunk_id(text: str, metadata: dict[str, Any], index: int) -> str:
    raw = "|".join(
        [
            str(metadata.get("filename", "")),
            str(metadata.get("user_id", "")),
            str(metadata.get("contract_id", "")),
            str(metadata.get("page", metadata.get("paragraph", metadata.get("slide", "")))),
            str(metadata.get("chunk_index", index)),
            text[:120],
        ]
    )
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _clean_metadata(metadata: dict[str, Any]) -> dict[str, str | int | float | bool]:
    clean = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            clean[key] = value
        else:
            clean[key] = str(value)
    return clean
