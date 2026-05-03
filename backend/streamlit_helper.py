"""Helper for Streamlit apps to interact with Foxtrot backend and Supabase.

This module provides a unified interface for Streamlit apps to:
1. Call the optimization API (or run in-process)
2. Save/load scenarios from Supabase
3. Handle both online (with backend) and offline (in-process) modes

Import this from your Streamlit app:
    from backend.streamlit_helper import optimize, save_scenario, get_scenarios
"""

import os
import requests
from typing import Dict, Any, List, Optional

# Try to import backend modules for in-process mode
try:
    from backend import optimizer as opt
    from backend import llm_layer as llm
    from backend import database as db
    BACKEND_AVAILABLE = True
except ImportError:
    BACKEND_AVAILABLE = False
    opt = None
    llm = None
    db = None


def optimize(
    budget: float,
    service_target: float,
    dept_id: int,
    season: str = "Fall/Holiday",
    backend_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Run optimization (tries API first, falls back to in-process).

    Args:
        budget: Budget in dollars.
        service_target: Target service level %.
        dept_id: Department ID.
        season: Season name.
        backend_url: Optional backend API URL (e.g., 'https://api.onrender.com').

    Returns:
        Optimization result dict.
    """

    # Try backend API first
    if backend_url:
        try:
            response = requests.post(
                f"{backend_url}/optimize",
                json={
                    "budget": budget,
                    "service_target": service_target,
                    "dept_id": dept_id,
                    "season": season,
                },
                timeout=30,
            )
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass

    # Fallback: in-process optimization
    if BACKEND_AVAILABLE and opt is not None:
        try:
            return opt.optimize_policy(budget, service_target, dept_id, season)
        except Exception as e:
            return {
                "feasible": False,
                "error": f"Optimization failed: {str(e)}",
                "configs": None,
            }

    return {
        "feasible": False,
        "error": "No backend available and in-process optimization failed",
        "configs": None,
    }


def scenario(
    nl_input: str,
    current_policy: Dict[str, Any],
    budget: float,
    service_target: float,
    dept_id: int,
    backend_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Run a what-if scenario."""

    if backend_url:
        try:
            response = requests.post(
                f"{backend_url}/scenario",
                json={
                    "nl_input": nl_input,
                    "current_policy": current_policy,
                    "budget": budget,
                    "service_target": service_target,
                    "dept_id": dept_id,
                },
                timeout=30,
            )
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass

    # Fallback: basic in-process scenario
    if BACKEND_AVAILABLE and opt is not None:
        try:
            # Simple budget adjustment without LLM
            new_budget = budget
            if "reduce" in nl_input.lower() or "cut" in nl_input.lower():
                new_budget = budget * 0.9
            elif "increase" in nl_input.lower() or "add" in nl_input.lower():
                new_budget = budget * 1.1

            result = opt.optimize_policy(new_budget, service_target, dept_id, "Fall/Holiday")
            result["narration"] = f"Scenario '{nl_input}': Adjusted budget to ${new_budget:,.0f}"
            return result
        except Exception as e:
            return {
                "feasible": False,
                "narration": f"Scenario failed: {str(e)}",
            }

    return {
        "feasible": False,
        "narration": "Scenario processing unavailable",
    }


def save_scenario(
    session_id: str,
    dept_id: int,
    dept_name: str,
    budget: float,
    service_target: float,
    feasible: bool,
    achieved_service: Optional[float] = None,
    total_cost: Optional[float] = None,
    configs: Optional[Dict] = None,
    narration: Optional[str] = None,
    nl_input: Optional[str] = None,
) -> Optional[str]:
    """Save scenario to Supabase (if available)."""
    if db is None:
        return None
    return db.save_scenario(
        session_id=session_id,
        dept_id=dept_id,
        dept_name=dept_name,
        budget=budget,
        service_target=service_target,
        season="Fall/Holiday",
        feasible=feasible,
        achieved_service=achieved_service,
        total_cost=total_cost,
        minimum_budget=None,
        configs=configs,
        narration=narration,
        nl_input=nl_input,
    )


def get_scenarios(session_id: str, limit: int = 50) -> List[Dict]:
    """Get scenario history from Supabase."""
    if db is None:
        return []
    return db.get_session_scenarios(session_id, limit)


def get_departments(backend_url: Optional[str] = None) -> Dict[str, Any]:
    """Get department list."""
    if backend_url:
        try:
            response = requests.get(f"{backend_url}/departments", timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass

    # Fallback: hardcoded departments
    return {
        "categories": [
            {"id": 1, "name": "Men's"},
            {"id": 2, "name": "Women's"},
            {"id": 3, "name": "Kids'"},
            {"id": 4, "name": "Home"},
            {"id": 5, "name": "Accessories"},
        ],
        "departments": [
            {"id": 101, "name": "Men's Shoes", "category_id": 1},
            {"id": 102, "name": "Men's Apparel", "category_id": 1},
            {"id": 104, "name": "Women's Shoes", "category_id": 2},
            {"id": 105, "name": "Women's Apparel", "category_id": 2},
        ],
    }
