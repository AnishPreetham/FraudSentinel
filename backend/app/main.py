import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.db.database import init_db
from app.api.health import router as health_router
from app.api.cases import router as cases_router
from app.api.investigations import router as investigations_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Fraud Investigation API...")
    await init_db()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down Fraud Investigation API")


app = FastAPI(
    title="Fraud Investigation API",
    description="TigerGraph Agentic Fraud Investigation System — HHGOA Hackathon",
    version="1.0.0",
    lifespan=lifespan,
)

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )


app.include_router(health_router)
app.include_router(cases_router, prefix="/api/cases")
app.include_router(investigations_router, prefix="/api/demo")


@app.get("/")
async def root():
    return {
        "service": "Fraud Investigation API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "hackathon": "HHGOA",
    }
