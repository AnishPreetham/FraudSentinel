import uuid
from fastapi import APIRouter
from app.api.cases import _active_cases
from app.api.demo import get_scenario, list_scenarios
from app.agent.workflow import run_investigation

router = APIRouter()


@router.get("/scenarios")
async def get_demo_scenarios():
    return {"scenarios": list_scenarios()}


@router.post("/scenario/{scenario_id}")
async def run_demo_scenario(scenario_id: str):
    scenario = get_scenario(scenario_id)
    if not scenario:
        return {"error": f"Scenario '{scenario_id}' not found", "available": list(["scenario_a", "scenario_b", "scenario_c", "scenario_d"])}

    case_id = f"DEMO-{scenario_id.upper()}-{str(uuid.uuid4())[:4].upper()}"
    result = await run_investigation(
        case_id=case_id,
        customer_id=scenario["customer_id"],
        account_id=scenario["account_id"],
        trigger=scenario["trigger_details"],
    )
    _active_cases[case_id] = result

    return {
        "case_id": case_id,
        "scenario": scenario["title"],
        "status": result.get("status"),
        "risk_level": result.get("risk_level"),
        "fraud_patterns": result.get("fraud_patterns", []),
        "recommended_action": result.get("recommendation", {}).get("action"),
        "confidence": result.get("confidence", 0),
    }
