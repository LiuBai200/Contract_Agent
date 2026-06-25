from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.db.session import init_db
from backend.routers import auth_router, chat_router, contract_router, health_router
from backend.services.rate_limiter import close_rate_limiter


app = FastAPI(
    title="Contract Review RAG Agent",
    description="Contract upload, user isolation, RAG retrieval, and risk review API.",
    version="0.4.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    init_db()


@app.on_event("shutdown")
async def shutdown_event():
    await close_rate_limiter()


app.include_router(health_router.router)
app.include_router(auth_router.router)
app.include_router(contract_router.router)
app.include_router(chat_router.router)
