from typing import Any, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    service: str


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)


class LoginRequest(BaseModel):
    username: str
    password: str


class UserPublic(BaseModel):
    id: int
    username: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User question for the contract agent.")
    session_id: Optional[str] = Field(None, description="Chat session id. Empty means create a new session.")
    contract_id: Optional[int] = Field(None, description="Selected contract id. Empty means search all contracts.")
    top_k: int = Field(5, ge=1, le=10)


class Citation(BaseModel):
    filename: Optional[str] = None
    page: Optional[int] = None
    paragraph: Optional[int] = None
    slide: Optional[int] = None
    clause_title: Optional[str] = None
    chunk_index: Optional[int] = None
    score: Optional[float] = None
    content: str


class AskResponse(BaseModel):
    answer: str
    model: str
    session_id: str
    citations: list[Citation] = Field(default_factory=list)


class DocumentPreview(BaseModel):
    page_content: str
    metadata: dict[str, Any]


class ChunkPreview(BaseModel):
    page_content: str
    metadata: dict[str, Any]


class UploadResponse(BaseModel):
    contract_id: Optional[int] = None
    filename: str
    saved_path: str
    size: int
    content_type: Optional[str] = None
    message: str
    document_count: int = 0
    documents: list[DocumentPreview] = Field(default_factory=list)
    chunk_count: int = 0
    stored_count: int = 0
    chunks: list[ChunkPreview] = Field(default_factory=list)


class ContractSummary(BaseModel):
    id: int
    filename: str
    size: int = 0
    document_count: int = 0
    chunk_count: int = 0
    created_at: str


class ContractDeleteResponse(BaseModel):
    contract_id: int
    filename: str
    deleted_chunks: int = 0
    message: str


class SessionSummary(BaseModel):
    id: str
    title: Optional[str] = None


class SessionDeleteResponse(BaseModel):
    session_id: str
    deleted_messages: int = 0
    message: str


class ChatMessagePublic(BaseModel):
    role: str
    content: str
    citations: list[Citation] = Field(default_factory=list)
