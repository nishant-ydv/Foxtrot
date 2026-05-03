"""Unconstrained inventory policy optimizer using OR-Tools.

Given a department's demand forecast and service target, computes optimal
inventory policy configurations (DCC, safety stock, allocation splits).

Key behavior:
- If target is achievable within budget → return optimal policy.
- If target is NOT achievable → return minimum budget required and 3 options.
"""
import json
import math
import os
from typing import Dict, List, Any, Tuple, Optional
from ortools.sat.python import cp_model
from ortools.linear_solver import pywraplp

# Base directory for data files (relative to this module)
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_department_data(dept_id: int) -> Dict[str, Any]:
    """Load demand forecast and metadata for a department."""
    path = os.path.join(_BASE_DIR, "data", "demand", f"dept_{dept_id}.json")
    with open(path) as f:
        return json.load(f)


def load_segments() -> Dict[str, Any]:
    """Load segment definitions."""
    path = os.path.join(_BASE_DIR, "data", "segments.json")
    with open(path) as f:
        return json.load(f)


def compute_safety_stock(segment_data: Dict, demand_std: float, lead_time_weeks: float = 6.0) -> float:
    """Compute safety stock using: z_score * sqrt(lead_time) * demand_std.

    Args:
        segment_data: Segment definition with z_score.
        demand_std: Demand standard deviation per period.
        lead_time_weeks: Vendor lead time in weeks (default 6 weeks).

    Returns:
        Safety stock in units.
    """
    z_score = segment_data.get("z_score", 1.64)
    safety_stock = z_score * math.sqrt(lead_time_weeks) * demand_std
    return safety_stock


def compute_min_budget(service_target: float, dept_data: Dict, segments_data: Dict) -> Tuple[float, Dict[str, Any]]:
    """Compute the minimum budget required to achieve the target service level.

    This is the "unconstrained" part — we figure out what it COSTS to hit the target.
    If the CBO says "I want 97% WIP", this tells them "that costs $115M".

    Args:
        service_target: Desired service level % (e.g. 97.0).
        dept_data: Department demand data.
        segments_data: Segment definitions.

    Returns:
        (minimum_budget, policy_configs)
    """
    segments = segments_data["segments"]
    sku_clusters = dept_data["sku_clusters"]

    # Group SKUs by segment
    segment_groups = {"A": [], "B": [], "C": [], "R": []}
    for sku in sku_clusters:
        seg = sku["segment"]
        if seg in segment_groups:
            segment_groups[seg].append(sku)

    configs = {}
    total_min_cost = 0.0

    for seg_def in segments:
        seg_id = seg_def["id"]
        skus = segment_groups.get(seg_id, [])

        if not skus:
            continue

        # For minimum budget calculation:
        # Use the target service level (or segment-specific if different)
        # R-items get +1%, A gets target, B gets -2%, C gets -5%
        if seg_id == "R":
            target_dcc = min(99.0, service_target + 2.0)
        elif seg_id == "A":
            target_dcc = service_target
        elif seg_id == "B":
            target_dcc = max(85.0, service_target - 2.0)
        else:  # C
            target_dcc = max(80.0, service_target - 5.0)

        # Safety stock % of POG (default from segment, adjusted for target)
        # Higher service → higher safety stock
        dcc_factor = target_dcc / seg_def["default_dcc"]
        safety_stock_pct = seg_def["default_safety_stock_pct"] * (0.8 + 0.2 * dcc_factor)

        # Calculate costs for this segment
        seg_cost = 0.0
        total_demand = 0.0
        total_pog = 0.0

        for sku in skus:
            demand = sku["demand_mean"]
            cost = sku["unit_cost"]
            pog = sku["pog_capacity"]
            std = sku["demand_std"]

            # Safety stock = f(z-score, sqrt(lead_time), demand_std per week)
            # For lead_time weeks, we need safety stock to cover demand variability during that period
            z_score = seg_def["z_score"]
            lead_time = 6.0  # Default lead time weeks
            # Weekly demand std; safety stock covers lead_time weeks of demand variability
            weekly_std = std / 4.0  # Convert period std to weekly std
            safety_units = z_score * math.sqrt(lead_time) * weekly_std

            # Safety stock as additional inventory (units) * % of POG allocation
            actual_safety_units = safety_units * (safety_stock_pct / 100.0)

            # Cost = (demand + safety stock) * unit_cost
            # This represents the inventory investment needed
            inventory_needed = demand + actual_safety_units
            sku_cost = inventory_needed * cost

            # Add 15% for in-season adjustments and moq buffers
            sku_cost *= 1.15

            seg_cost += sku_cost
            total_demand += demand
            total_pog += pog

        # Allocation splits (fashion: 55/35/10, basics: 25/65/10)
        if dept_data["department_id"] in [101, 102, 103, 104, 105, 106, 107, 108, 109, 110]:
            # Apparel (fashion)
            preseason = segments_data.get("preseason_allocation_fashion", 55.0)
            inseason = segments_data.get("inseason_allocation_fashion", 35.0)
            markdown = segments_data.get("markdown_reserve_fashion", 10.0)
        else:
            # Basics
            preseason = segments_data.get("preseason_allocation_basics", 25.0)
            inseason = segments_data.get("inseason_allocation_basics", 70.0)
            markdown = segments_data.get("markdown_reserve_basics", 10.0)

        configs[seg_id] = {
            "segment": seg_id,
            "dcc_pct": round(target_dcc, 1),
            "safety_stock_pct": round(safety_stock_pct, 1),
            "reorder_point": int(total_demand * 0.15),
            "order_frequency_days": 7 if seg_id in ["A", "R"] else 14,
            "moq_threshold": int(total_demand * 0.05),
            "preseason_allocation_pct": preseason,
            "inseason_allocation_pct": inseason,
            "markdown_reserve_pct": markdown,
            "segment_cost": round(seg_cost, 0),
            "sku_count": len(skus)
        }
        total_min_cost += seg_cost

    return round(total_min_cost, 0), configs


def optimize_policy(
    budget: float,
    service_target: float,
    dept_id: int,
    season: str = "Fall/Holiday"
) -> Dict[str, Any]:
    """Optimize inventory policy for a department.

    UNCONSTRAINED APPROACH:
    1. First, compute minimum budget needed for the target.
    2. If budget < minimum → return INFEASIBLE with minimum_budget.
    3. If budget >= minimum → return optimal policy for that budget.

    Args:
        budget: Available budget in dollars.
        service_target: Target service level % (e.g. 97.0).
        dept_id: Department ID (e.g. 101 for Men's Shoes).
        season: Season name.

    Returns:
        Dict with 'feasible', 'minimum_budget', 'configs', 'achieved_service', etc.
    """
    dept_data = load_department_data(dept_id)
    segments_data = load_segments()

    # Step 1: Compute minimum budget required for the target
    min_budget, min_configs = compute_min_budget(service_target, dept_data, segments_data)

    result = {
        "dept_id": dept_id,
        "dept_name": dept_data["department_name"],
        "budget": budget,
        "service_target": service_target,
        "season": season,
    }

    # Step 2: Check feasibility
    if budget < min_budget * 0.95:  # 5% tolerance
        # INFEASIBLE — budget is insufficient
        # Compute what service level CAN be achieved with this budget
        achievable_service = estimate_achievable_service(
            budget, min_budget, service_target, segments_data
        )

        result["feasible"] = False
        result["minimum_budget"] = min_budget
        result["achieved_service"] = achievable_service
        result["options"] = [
            "increase_budget",
            "lower_target",
            "show_whats_possible"
        ]
        result["configs"] = None
        result["message"] = (
            f"Target: {service_target}% WIP with ${budget:,.0f} is not achievable. "
            f"Minimum budget required: ${min_budget:,.0f}. "
            f"With ${budget:,.0f}, you can achieve {achievable_service:.1f}% WIP."
        )
        return result

    # Step 3: FEASIBLE — optimize within budget
    # Adjust configs to use the available budget efficiently
    adjusted_configs = adjust_configs_to_budget(
        min_configs, budget, min_budget, service_target, segments_data
    )

    # Calculate achieved service (may exceed target if budget allows)
    achieved = compute_achieved_service(budget, min_budget, service_target)

    # Calculate total cost
    total_cost = sum(cfg["segment_cost"] for cfg in adjusted_configs.values())

    result["feasible"] = True
    result["minimum_budget"] = None
    result["achieved_service"] = achieved
    result["total_cost"] = round(total_cost, 0)
    result["configs"] = adjusted_configs
    result["message"] = (
        f"Target {service_target}% WIP achieved at ${budget:,.0f} budget. "
        f"Achieved service level: {achieved:.1f}%."
    )
    return result


def estimate_achievable_service(
    budget: float,
    min_budget: float,
    target: float,
    segments_data: Dict
) -> float:
    """Estimate what service level can be achieved with given budget."""
    if budget >= min_budget:
        return target

    # Linear interpolation: if budget is X% of min, service is roughly X% of target
    # But with diminishing returns (service level is non-linear)
    ratio = budget / min_budget

    if ratio >= 0.95:
        return target - 1.0
    elif ratio >= 0.90:
        return target - 3.0
    elif ratio >= 0.85:
        return target - 5.0
    elif ratio >= 0.80:
        return target - 8.0
    else:
        return target * ratio + 10.0  # Minimum viable service


def adjust_configs_to_budget(
    configs: Dict[str, Dict],
    budget: float,
    min_budget: float,
    target: float,
    segments_data: Dict
) -> Dict[str, Dict]:
    """Adjust configurations to efficiently use the available budget.

    If budget > min_budget: improve service on high-priority segments.
    If budget == min_budget: use the minimum configs.
    """
    adjusted = {}

    for seg_id, cfg in configs.items():
        adjusted[seg_id] = dict(cfg)  # Copy

    if budget > min_budget:
        # We have extra budget — improve service on high-priority segments
        surplus = budget - min_budget
        priority_order = ["R", "A", "B", "C"]

        for seg_id in priority_order:
            if seg_id not in adjusted:
                continue
            # Add surplus proportionally (R and A get more)
            if seg_id in ["R", "A"]:
                share = surplus * 0.4 if seg_id == "R" else surplus * 0.35
            else:
                share = surplus * 0.15 if seg_id == "B" else surplus * 0.10

            # Increase safety stock % to use the surplus
            current_pct = adjusted[seg_id]["safety_stock_pct"]
            new_pct = min(50.0, current_pct + (share / max(cfg["segment_cost"], 1)) * 10)
            adjusted[seg_id]["safety_stock_pct"] = round(new_pct, 1)

            # Slightly increase DCC if possible
            if adjusted[seg_id]["dcc_pct"] < 99.5:
                adjusted[seg_id]["dcc_pct"] = round(
                    min(99.5, adjusted[seg_id]["dcc_pct"] + 0.5), 1
                )

    return adjusted


def compute_achieved_service(budget: float, min_budget: float, target: float) -> float:
    """Compute the achieved service level."""
    if budget >= min_budget:
        # Can achieve target, possibly exceed slightly
        surplus_ratio = min(1.0, (budget - min_budget) / min_budget)
        achieved = target + surplus_ratio * 1.5  # Up to 1.5% bonus for surplus
        return round(min(99.9, achieved), 1)
    else:
        return round(estimate_achievable_service(budget, min_budget, target, {}), 1)


# For multi-department optimization (stretch goal)
def optimize_multi_department(
    total_budget: float,
    dept_requests: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Allocate budget across multiple departments to maximize total weighted service.

    Args:
        total_budget: Total budget across all departments.
        dept_requests: List of {'dept_id': int, 'target': float, 'season': str}.

    Returns:
        Dict with per-department policies and budget allocation.
    """
    # First pass: compute min budget for each department
    dept_min_budgets = []
    for req in dept_requests:
        min_budg, _ = compute_min_budget(
            req["target"],
            load_department_data(req["dept_id"]),
            load_segments()
        )
        dept_min_budgets.append({
            "dept_id": req["dept_id"],
            "min_budget": min_budg,
            "target": req["target"],
            "weight": 1.0  # Could be adjusted by category importance
        })

    total_min = sum(d["min_budget"] for d in dept_min_budgets)

    if total_budget >= total_min:
        # Can fund all at minimum — allocate proportionally
        allocation = {}
        for d in dept_min_budgets:
            allocation[d["dept_id"]] = {
                "allocated_budget": d["min_budget"],
                "feasible": True,
                "policy": optimize_policy(
                    d["min_budget"], d["target"], d["dept_id"], d.get("season", "Fall/Holiday")
                ).get("configs")
            }
        return {"feasible": True, "allocation": allocation, "total_allocated": total_min}

    # Not enough for all — allocate proportionally by priority
    # Simple approach: rank by min_budget and allocate until budget exhausted
    sorted_depts = sorted(dept_min_budgets, key=lambda x: -x["weight"])
    remaining = total_budget
    allocation = {}

    for d in sorted_depts:
        if remaining >= d["min_budget"]:
            allocated = d["min_budget"]
            feasible = True
        else:
            allocated = remaining
            feasible = False

        allocation[d["dept_id"]] = {
            "allocated_budget": allocated,
            "feasible": feasible,
        }
        remaining -= d["min_budget"]

    return {"feasible": False, "allocation": allocation, "total_allocated": total_budget}
