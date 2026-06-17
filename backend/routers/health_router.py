from fastapi import APIRouter

from backend.schemas import HealthResponse


router = APIRouter(tags=["health"])


@router.get("/", response_model=HealthResponse)
async def root():
    return HealthResponse(status="ok", service="contract-rag-agent")


@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", service="contract-rag-agent")
