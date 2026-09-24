import json
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.db.database import CaseMemoryRecord


async def store_case_memory(db: AsyncSession, case_id: str, summary: str, fraud_patterns: list, outcome: str):
    record = CaseMemoryRecord(
        case_id=case_id,
        summary=summary,
        fraud_patterns=json.dumps(fraud_patterns),
        outcome=outcome,
        embeddings_json=json.dumps({"patterns": fraud_patterns, "outcome": outcome}),
        created_at=datetime.utcnow()
    )
    db.add(record)
    await db.commit()


async def find_similar_cases(db: AsyncSession, features: dict, limit: int = 5) -> list[dict]:
    result = await db.execute(select(CaseMemoryRecord).limit(limit))
    records = result.scalars().all()

    feature_patterns = set(features.get("fraud_patterns", []))
    similar = []
    for r in records:
        stored_patterns = set(json.loads(r.fraud_patterns))
        overlap = len(feature_patterns & stored_patterns)
        if overlap > 0 or not feature_patterns:
            similarity = overlap / max(len(feature_patterns | stored_patterns), 1)
            similar.append({
                "case_id": r.case_id,
                "similarity": round(similarity, 2),
                "summary": r.summary,
                "outcome": r.outcome,
                "fraud_patterns": json.loads(r.fraud_patterns),
                "created_at": r.created_at.isoformat() if r.created_at else None,
            })
    similar.sort(key=lambda x: x["similarity"], reverse=True)
    return similar[:limit]


async def get_memory_for_investigation(db: AsyncSession, customer_id: str, patterns: list) -> list[dict]:
    return await find_similar_cases(db, {"fraud_patterns": patterns}, limit=3)
