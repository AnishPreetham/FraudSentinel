"""API integration tests using httpx AsyncClient."""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.database import init_db


@pytest.fixture(autouse=True)
def setup_db():
    """Ensure DB tables exist before each test (sync wrapper for pytest-asyncio 0.23)."""
    import asyncio
    asyncio.get_event_loop().run_until_complete(init_db())


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_ready_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert "checks" in data
    assert "integrations" in data
    assert data["integrations"]["database"] == "sqlite"


@pytest.mark.asyncio
async def test_demo_scenario_a():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", timeout=60) as client:
        resp = await client.post("/api/demo/scenario/scenario_a")
    assert resp.status_code == 200
    data = resp.json()
    assert "case_id" in data
    assert data["risk_level"] in ("HIGH", "CRITICAL")
    assert data["recommended_action"] is not None


@pytest.mark.asyncio
async def test_demo_scenario_b():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", timeout=60) as client:
        resp = await client.post("/api/demo/scenario/scenario_b")
    assert resp.status_code == 200
    assert "case_id" in resp.json()


@pytest.mark.asyncio
async def test_demo_scenario_c():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", timeout=60) as client:
        resp = await client.post("/api/demo/scenario/scenario_c")
    assert resp.status_code == 200
    data = resp.json()
    assert data["risk_level"] in ("HIGH", "CRITICAL")


@pytest.mark.asyncio
async def test_get_case_after_demo():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", timeout=60) as client:
        create_resp = await client.post("/api/demo/scenario/scenario_a")
        case_id = create_resp.json()["case_id"]
        get_resp = await client.get(f"/api/cases/{case_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["case_id"] == case_id
    assert len(data["evidence"]) > 0
    assert len(data["investigation_timeline"]) > 0


@pytest.mark.asyncio
async def test_list_cases():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", timeout=60) as client:
        await client.post("/api/demo/scenario/scenario_a")
        resp = await client.get("/api/cases")
    assert resp.status_code == 200
    assert "cases" in resp.json()


@pytest.mark.asyncio
async def test_approve_action():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", timeout=60) as client:
        create_resp = await client.post("/api/demo/scenario/scenario_a")
        case_id = create_resp.json()["case_id"]
        resp = await client.post(
            f"/api/cases/{case_id}/approve",
            json={"approved": True, "approver_id": "test_analyst", "reason": "Verified fraud ring"}
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["execution_status"] == "EXECUTED"


@pytest.mark.asyncio
async def test_reject_action():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", timeout=60) as client:
        create_resp = await client.post("/api/demo/scenario/scenario_a")
        case_id = create_resp.json()["case_id"]
        resp = await client.post(
            f"/api/cases/{case_id}/approve",
            json={"approved": False, "approver_id": "test_analyst", "reason": "Needs more review"}
        )
    assert resp.status_code == 200
    assert resp.json()["execution_status"] == "REJECTED"


@pytest.mark.asyncio
async def test_unknown_scenario_returns_error():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/demo/scenario/nonexistent")
    assert resp.status_code == 200
    assert "error" in resp.json()


@pytest.mark.asyncio
async def test_get_nonexistent_case_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/cases/CASE-DOESNOTEXIST")
    assert resp.status_code == 404
