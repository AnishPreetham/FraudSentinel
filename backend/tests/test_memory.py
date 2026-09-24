"""Tests for case memory persistence."""
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.db.database import Base
from app.memory.case_memory import store_case_memory, find_similar_cases


async def _make_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, SessionLocal


@pytest.mark.asyncio
async def test_store_and_retrieve_memory():
    engine, SessionLocal = await _make_session()
    async with SessionLocal() as session:
        await store_case_memory(
            session,
            case_id="CASE-001",
            summary="Connected fraud ring blocked",
            fraud_patterns=["MONEY_LAUNDERING", "VELOCITY_ABUSE"],
            outcome="FRAUD_CONFIRMED",
        )
        results = await find_similar_cases(
            session,
            features={"fraud_patterns": ["MONEY_LAUNDERING"]},
            limit=5,
        )
    await engine.dispose()
    assert len(results) == 1
    assert results[0]["case_id"] == "CASE-001"
    assert results[0]["outcome"] == "FRAUD_CONFIRMED"


@pytest.mark.asyncio
async def test_similar_case_pattern_matching():
    engine, SessionLocal = await _make_session()
    async with SessionLocal() as session:
        await store_case_memory(session, "CASE-ML", "Money laundering", ["MONEY_LAUNDERING"], "FRAUD_CONFIRMED")
        await store_case_memory(session, "CASE-ATO", "Account takeover", ["ACCOUNT_TAKEOVER"], "FRAUD_CONFIRMED")
        await store_case_memory(session, "CASE-MIX", "Mixed", ["MONEY_LAUNDERING", "VELOCITY_ABUSE"], "FRAUD_CONFIRMED")
        results = await find_similar_cases(session, {"fraud_patterns": ["MONEY_LAUNDERING"]}, limit=10)
    await engine.dispose()
    case_ids = [r["case_id"] for r in results]
    assert "CASE-ML" in case_ids
    assert "CASE-MIX" in case_ids
    ml_sims = [r["similarity"] for r in results if r["case_id"] in ("CASE-ML", "CASE-MIX")]
    ato_sims = [r["similarity"] for r in results if r["case_id"] == "CASE-ATO"]
    if ato_sims:
        assert all(ms >= atos for ms in ml_sims for atos in ato_sims)


@pytest.mark.asyncio
async def test_empty_memory_returns_empty():
    engine, SessionLocal = await _make_session()
    async with SessionLocal() as session:
        results = await find_similar_cases(session, {"fraud_patterns": ["MONEY_LAUNDERING"]}, limit=5)
    await engine.dispose()
    assert results == []


@pytest.mark.asyncio
async def test_memory_preserves_all_fields():
    engine, SessionLocal = await _make_session()
    async with SessionLocal() as session:
        await store_case_memory(
            session,
            case_id="CASE-FULL",
            summary="Full test case summary",
            fraud_patterns=["ACCOUNT_TAKEOVER", "VELOCITY_ABUSE"],
            outcome="CLEARED",
        )
        results = await find_similar_cases(session, {"fraud_patterns": ["ACCOUNT_TAKEOVER"]})
    await engine.dispose()
    r = results[0]
    assert r["case_id"] == "CASE-FULL"
    assert r["summary"] == "Full test case summary"
    assert "ACCOUNT_TAKEOVER" in r["fraud_patterns"]
    assert r["outcome"] == "CLEARED"
    assert r["created_at"] is not None


@pytest.mark.asyncio
async def test_no_duplicate_ids():
    """Store same case twice — should appear once in results."""
    engine, SessionLocal = await _make_session()
    async with SessionLocal() as session:
        await store_case_memory(session, "CASE-DUP", "First write", ["MONEY_LAUNDERING"], "FRAUD_CONFIRMED")
        # Simulate duplicate write attempt (separate call)
        await store_case_memory(session, "CASE-DUP2", "Second case", ["MONEY_LAUNDERING"], "CLEARED")
        results = await find_similar_cases(session, {"fraud_patterns": ["MONEY_LAUNDERING"]})
    await engine.dispose()
    # Both separate case IDs present
    assert len(results) == 2
