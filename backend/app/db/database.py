import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, String, Float, DateTime, Text, Boolean, Integer
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./fraud_investigation.db")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class CaseRecord(Base):
    __tablename__ = "cases"
    id = Column(String, primary_key=True)
    status = Column(String, default="NEW")
    risk_score = Column(Float, default=0.0)
    risk_level = Column(String, default="LOW")
    customer_id = Column(String, nullable=False)
    account_id = Column(String, nullable=False)
    trigger_type = Column(String, nullable=False)
    trigger_details = Column(Text, default="{}")
    fraud_patterns = Column(Text, default="[]")
    evidence = Column(Text, default="[]")
    uncertainty = Column(Text, default="{}")
    recommendation = Column(Text, default="{}")
    investigation_timeline = Column(Text, default="[]")
    agent_reasoning = Column(Text, default="")
    similar_cases = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class InvestigationEvent(Base):
    __tablename__ = "investigation_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    event_data = Column(Text, default="{}")
    timestamp = Column(DateTime, default=datetime.utcnow)


class EvidenceRecord(Base):
    __tablename__ = "evidence_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String, nullable=False)
    evidence_type = Column(String, nullable=False)
    source = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    reliability = Column(Float, default=0.8)
    created_at = Column(DateTime, default=datetime.utcnow)


class RecommendationRecord(Base):
    __tablename__ = "recommendations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String, nullable=False)
    action = Column(String, nullable=False)
    reason = Column(Text, nullable=False)
    confidence = Column(Float, default=0.0)
    policy_basis = Column(Text, default="")
    requires_approval = Column(Boolean, default=False)
    status = Column(String, default="RECOMMENDED")
    created_at = Column(DateTime, default=datetime.utcnow)


class CaseMemoryRecord(Base):
    __tablename__ = "case_memory"
    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String, nullable=False)
    summary = Column(Text, nullable=False)
    fraud_patterns = Column(Text, default="[]")
    outcome = Column(String, nullable=False)
    embeddings_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
