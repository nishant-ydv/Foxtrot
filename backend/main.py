"""Foxtrot Backend API — FastAPI application.

Endpoints:
- GET /departments — List all 50 departments with categories.
- POST /optimize — Optimize policy for a department (unconstrained).
- POST /scenario — Run a what-if scenario with LLM narration.
- POST /decision — Frame a high-stakes decision.
- POST /optimize/multi — Multi-department budget allocation (stretch).
"""
import json
import os
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from models import (
    OptimizeRequest, OptimizeResponse, ScenarioRequest, ScenarioResponse,
    DecisionRequest, DecisionResponse, DepartmentsResponse,
    DepartmentInfo, CategoryInfo, PolicyConfig,
    PolicyApprovalRequest, PolicyApprovalResponse
)
# Optimizer import with fallback (same pattern as frontend/app.py)
try:
    import optimizer as opt
except ImportError:
    try:
        import optimizer_simple as opt
    except ImportError:
        opt = None
import llm_layer as llm

# Base directory for data files
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# Initialize FastAPI app
app = FastAPI(
    title="Foxtrot API",
    description="AI-powered inventory policy optimization for retail CBOs",
    version="0.1.0"
)

# CORS middleware for Streamlit frontend
_cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Helper functions ---

def _load_categories():
    """Load categories from JSON."""
    with open(os.path.join(_BASE_DIR, "data", "categories.json")) as f:
        return json.load(f)


def _load_departments():
    """Load departments from JSON."""
    with open(os.path.join(_BASE_DIR, "data", "departments.json")) as f:
        return json.load(f)


def _policy_configs_to_response(configs: Dict[str, Dict]) -> Dict[str, PolicyConfig]:
    """Convert optimizer config dicts to Pydantic PolicyConfig objects."""
    result = {}
    for seg_id, cfg in configs.items():
        result[seg_id] = PolicyConfig(
            segment=cfg["segment"],
            dcc_pct=cfg["dcc_pct"],
            safety_stock_pct=cfg["safety_stock_pct"],
            reorder_point=cfg["reorder_point"],
            order_frequency_days=cfg["order_frequency_days"],
            moq_threshold=cfg["moq_threshold"],
            preseason_allocation_pct=cfg["preseason_allocation_pct"],
            inseason_allocation_pct=cfg["inseason_allocation_pct"],
            end_of_season_pct=cfg["end_of_season_pct"]
        )
    return result


# --- Endpoints ---

@app.get("/departments", response_model=DepartmentsResponse)
async def get_departments():
    """List all 50 departments with their categories."""
    categories_data = _load_categories()
    departments_data = _load_departments()

    categories = [CategoryInfo(id=c["id"], name=c["name"]) for c in categories_data]
    departments = [
        DepartmentInfo(id=d["id"], name=d["name"], category_id=d["category_id"])
        for d in departments_data
    ]

    return DepartmentsResponse(categories=categories, departments=departments)


@app.post("/optimize", response_model=OptimizeResponse)
async def optimize(request: OptimizeRequest):
    """Optimize inventory policy for a department or multiple departments/categories.

    UNCONSTRAINED: If budget insufficient, returns minimum budget needed + 3 options.
    If feasible, returns optimal policy configs.

    Supports:
    - Single department: provide dept_id
    - Multiple departments: provide dept_ids list
    - Multiple categories: provide category_ids list (maps to all depts in those categories)
    """
    if opt is None:
        raise HTTPException(status_code=503, detail="Optimizer not available (OR-Tools and simple optimizer both missing)")
    try:
        # Determine which departments to optimize
        dept_list = []

        if request.category_ids:
            # Map category IDs to department IDs
            dept_list = opt.get_dept_ids_by_category(request.category_ids)
        elif request.dept_ids:
            dept_list = request.dept_ids
        elif request.dept_id:
            dept_list = [request.dept_id]
        else:
            raise HTTPException(status_code=400, detail="Must provide dept_id, dept_ids, or category_ids")

        # Multi-department optimization
        if len(dept_list) > 1:
            dept_requests = [
                {"dept_id": d, "target": request.service_target, "season": request.season}
                for d in dept_list
            ]
            multi_result = opt.optimize_multi_department(request.budget, dept_requests)

            # Convert to OptimizeResponse format
            per_dept_configs = {}
            if multi_result.get("allocation"):
                for dept_id, alloc in multi_result["allocation"].items():
                    if alloc.get("policy"):
                        per_dept_configs[dept_id] = alloc["policy"]

            return OptimizeResponse(
                feasible=multi_result.get("feasible", False),
                total_cost=multi_result.get("total_allocated"),
                per_department_configs=per_dept_configs,
                aggregated_summary={"total_departments": len(dept_list), "budget": request.budget},
                options=["increase_budget", "lower_target"] if not multi_result.get("feasible") else None
            )

        # Single department optimization
        result = opt.optimize_policy(
            budget=request.budget,
            service_target=request.service_target,
            dept_id=dept_list[0],
            season=request.season,
            return_sku_level=request.return_sku_level
        )

        # Convert configs to Pydantic models if present
        configs_response = None
        if result.get("configs"):
            configs_response = _policy_configs_to_response(result["configs"])

        sku_configs = result.get("sku_configs")

        return OptimizeResponse(
            feasible=result["feasible"],
            minimum_budget=result.get("minimum_budget"),
            achieved_service=result.get("achieved_service"),
            total_cost=result.get("total_cost"),
            budget_remaining=result.get("budget_remaining"),
            budget_remaining_millions=result.get("budget_remaining_millions"),
            markdown_risk=result.get("markdown_risk"),
            sales_loss_risk=result.get("sales_loss_risk"),
            configs=configs_response,
            sku_configs=sku_configs,
            options=result.get("options"),
            narration=result.get("narration"),
            dept_id=result.get("dept_id"),
            dept_name=result.get("dept_name")
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Department not found: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")


@app.post("/scenario", response_model=ScenarioResponse)
async def scenario(request: ScenarioRequest):
    """Run a what-if scenario with LLM-powered trade-off narration.

    Parses natural language scenario, re-optimizes, and narrates trade-offs.
    """
    try:
        # Parse scenario with LLM
        llm_response = llm.parse_scenario(
            nl_input=request.nl_input,
            current_policy=request.current_policy,
            budget=request.budget,
            service_target=request.service_target
        )

        if llm_response.get("error"):
            # LLM failed — return basic response
            return ScenarioResponse(
                feasible=True,
                narration=f"Scenario '{request.nl_input}' noted. LLM narration unavailable.",
                budget_change=0.0,
                service_change=0.0
            )

        # Adjust budget/target based on parsed action
        new_budget = request.budget
        new_target = request.service_target

        action = llm_response.get("action", "unknown")
        value = llm_response.get("value", 0)

        if action == "reduce_budget":
            new_budget = max(0, request.budget - abs(value))
        elif action == "increase_budget":
            new_budget = request.budget + abs(value)
        elif action == "reduce_target":
            new_target = max(50.0, request.service_target - abs(value))
        elif action == "increase_target":
            new_target = min(99.9, request.service_target + abs(value))

        # Re-optimize with new parameters
        new_result = opt.optimize_policy(
            budget=new_budget,
            service_target=new_target,
            dept_id=request.dept_id
        )

        # Generate LLM narration for trade-offs
        narration = llm.narrate_tradeoff(
            old_policy={"service": request.service_target, "configs": request.current_policy},
            new_policy=new_result,
            budget_change=new_budget - request.budget,
            service_change=new_result.get("achieved_service", 0) - request.service_target
        )

        # Convert configs
        configs_response = None
        if new_result.get("feasible") and new_result.get("configs"):
            configs_response = _policy_configs_to_response(new_result["configs"])

        return ScenarioResponse(
            feasible=new_result["feasible"],
            configs=configs_response,
            narration=narration,
            budget_change=new_budget - request.budget,
            service_change=new_result.get("achieved_service", 0) - request.service_target
        )

    except Exception as e:
        return ScenarioResponse(
            feasible=False,
            narration=f"Scenario processing failed: {str(e)}",
            budget_change=0.0,
            service_change=0.0
        )


@app.post("/decision", response_model=DecisionResponse)
async def decision(request: DecisionRequest):
    """Frame a high-stakes decision with quantified trade-offs."""
    try:
        llm_response = llm.frame_decision(
            decision_context=request.decision_context,
            dept_id=request.dept_id,
            budget=request.budget,
            current_service=request.current_service
        )

        return DecisionResponse(
            context=request.decision_context,
            options=llm_response.get("options", []),
            recommendation=llm_response.get("recommendation", "Unknown")
        )
    except Exception as e:
        return DecisionResponse(
            context=request.decision_context,
            options=[],
            recommendation=f"Error: {str(e)}"
        )


@app.post("/optimize/multi")
async def optimize_multi(request: Dict[str, Any]):
    """Multi-department budget allocation (stretch goal).

    Allocates total budget across multiple departments to maximize
    total weighted service level.
    """
    try:
        total_budget = request.get("total_budget", 0)
        dept_requests = request.get("departments", [])

        result = opt.optimize_multi_department(total_budget, dept_requests)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Multi-department optimization failed: {str(e)}")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}


# --- Policy Approval Endpoints ---

def _load_approvals():
    """Load approvals from JSON file."""
    path = os.path.join(_BASE_DIR, "data", "approvals.json")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


def _save_approvals(approvals: list):
    """Save approvals to JSON file."""
    path = os.path.join(_BASE_DIR, "data", "approvals.json")
    try:
        with open(path, "w") as f:
            json.dump(approvals, f, indent=2)
    except (OSError, IOError) as e:
        print(f"[Approvals] Failed to save: {e}", file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"Failed to save approval: {str(e)}")


@app.post("/policy/approve", response_model=PolicyApprovalResponse)
async def approve_policy(request: PolicyApprovalRequest):
    """Approve a policy and store it for downstream integration."""
    try:
        import datetime
        approval_id = f"APR-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"

        approval = {
            "approval_id": approval_id,
            "policy_id": request.policy_id,
            "approver": request.approver,
            "approval_notes": request.approval_notes,
            "status": "approved",
            "timestamp": datetime.datetime.now().isoformat(),
            "approved_policy": request.approved_policy
        }

        # Save to file-based store
        approvals = _load_approvals()
        approvals.append(approval)
        _save_approvals(approvals)

        return PolicyApprovalResponse(
            approval_id=approval_id,
            status="approved",
            timestamp=approval["timestamp"],
            approved_policy=request.approved_policy,
            approver=request.approver
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Approval failed: {str(e)}")


@app.get("/policy/approvals")
async def list_approvals():
    """List all policy approvals."""
    try:
        approvals = _load_approvals()
        return {"approvals": approvals, "count": len(approvals)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load approvals: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
