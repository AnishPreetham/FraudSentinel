from fastapi import APIRouter
from datetime import datetime
import os

router = APIRouter()


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "fraud-investigation-api",
        "version": "1.0.0",
    }


@router.get("/ready")
async def ready():
    from app.agent.llm import llm_available
    tg_host = os.getenv("TIGERGRAPH_HOST", "")
    checks = {
        "api": True,
        "database": True,
        "tigergraph": bool(tg_host and os.getenv("TIGERGRAPH_PASSWORD")),
        "llm": llm_available(),
    }
    all_critical = checks["api"] and checks["database"]
    return {
        "ready": all_critical,
        "checks": checks,
        "mode": (
            "full" if (checks["tigergraph"] and checks["llm"])
            else "llm_only" if checks["llm"]
            else "graph_only" if checks["tigergraph"]
            else "demo_mock"
        ),
        "integrations": {
            "tigergraph": "real" if checks["tigergraph"] else "mock",
            "llm": "real" if checks["llm"] else "deterministic_fallback",
            "database": "sqlite",
        }
    }
