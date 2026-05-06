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


def _inverse_normal_cdf(p: float) -> float:
    """Approximate inverse CDF of standard normal (Acklam's approximation)."""
    if p <= 0:
        return float('-inf')
    if p >= 1:
        return float('inf')
    if p == 0.5:
        return 0.0
    if p < 0.5:
        t = math.sqrt(-2.0 * math.log(p))
        c0, c1, c2 = 2.515517, 0.802853, 0.010328
        d1, d2, d3 = 1.432788, 0.189269, 0.001308
        return -(t - (c0 + c1*t + c2*t*t) / (1.0 + d1*t + d2*t*t + d3*t*t*t))
    else:
        t = math.sqrt(-2.0 * math.log(1.0 - p))
        c0, c1, c2 = 2.515517, 0.802853, 0.010328
        d1, d2, d3 = 1.432788, 0.189269, 0.001308
        return t - (c0 + c1*t + c2*t*t) / (1.0 + d1*t + d2*t*t + d3*t*t*t)

# Base directory for data files (relative to this module)
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_department_data(dept_id: int) -> Dict[str, Any]:
    """Load demand forecast and metadata for a department."""
    path = os.path.join(_BASE_DIR, "data", "demand", f"dept_{dept_id}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Demand file not found: {path}")
    with open(path) as f:
        data = json.load(f)
    # Validate structure
    if not data.get("sku_clusters"):
        raise ValueError(f"Department {dept_id}: 'sku_clusters' is empty or missing")
    for sku in data["sku_clusters"]:
        if not sku.get("demand_mean") or sku.get("demand_mean", 0) <= 0:
            raise ValueError(f"Department {dept_id}: SKU {sku.get('sku_id')} has invalid demand_mean")
    return data


def load_segments() -> Dict[str, Any]:
    """Load segment definitions."""
    path = os.path.join(_BASE_DIR, "data", "segments.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Segments file not found: {path}")
    with open(path) as f:
        data = json.load(f)
    if not data.get("segments"):
        raise ValueError("Segments file has no 'segments' data")
    return data


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

    MOQ (minimum order quantity) thresholds are computed per segment as 5% of total
    segment demand (not user-provided).

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
        # R-items (must-have) get highest priority, then A, then B/C
        # Use minimum floors to protect high-priority segments even at low service targets
        if seg_id == "R":
            target_dcc = min(99.0, max(95.0, service_target + 2.0))
        elif seg_id == "A":
            target_dcc = max(85.0, service_target)
        elif seg_id == "B":
            target_dcc = max(75.0, service_target - 2.0)
        else:  # C
            target_dcc = max(70.0, service_target - 5.0)

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
            z_score = _inverse_normal_cdf(target_dcc / 100.0)
            lead_time = 6.0  # Default lead time weeks
            # Weekly demand std; safety stock covers lead_time weeks of demand variability
            weekly_std = std / 4.0  # Convert period std to weekly std
            statistical_safety = z_score * math.sqrt(lead_time) * weekly_std

            # Business rule: safety stock must be at least (pct * target_dcc/100) of POG
            # This scales the POG floor proportionally with the target service level
            scaled_pct = safety_stock_pct * (target_dcc / 100.0)
            min_safety_from_pog = pog * (scaled_pct / 100.0)

            # Use the max: statistical safety (scales with service) or business minimum
            actual_safety_units = max(statistical_safety, min_safety_from_pog)

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
            end_of_season = segments_data.get("markdown_reserve_fashion", 10.0)
        else:
            # Basics
            preseason = segments_data.get("preseason_allocation_basics", 25.0)
            inseason = segments_data.get("inseason_allocation_basics", 70.0)
            end_of_season = segments_data.get("markdown_reserve_basics", 10.0)

        configs[seg_id] = {
            "segment": seg_id,
            "dcc_pct": round(target_dcc, 1),
            "safety_stock_pct": round(safety_stock_pct, 1),
            "reorder_point": int(total_demand * 0.15),
            "order_frequency_days": 7 if seg_id in ["A", "R"] else 14,
            # MOQ threshold: 5% of total segment demand (computed, not user input)
            "moq_threshold": int(total_demand * 0.05),
            "preseason_allocation_pct": preseason,
            "inseason_allocation_pct": inseason,
            "end_of_season_pct": end_of_season,
            "segment_cost": round(seg_cost, 0),
            "sku_count": len(skus)
        }
        total_min_cost += seg_cost

    return round(total_min_cost, 0), configs


# optimize_policy function is defined later in the file with return_sku_level parameter


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
    """Adjust configurations to fit the available budget.

    If budget > min_budget: improve service on high-priority segments (R > A > B > C).
    If budget < min_budget: reduce low-priority segments first (C > B > A > R).
    If budget == min_budget: return configs unchanged.
    """
    adjusted = {}

    for seg_id, cfg in configs.items():
        adjusted[seg_id] = dict(cfg)  # Copy

    if budget >= min_budget:
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
    else:
        # Budget is insufficient — reduce low-priority segments first
        deficit = min_budget - budget
        # Reverse priority: cut C first, then B, protect A, fully protect R
        reduction_order = ["C", "B", "A", "R"]
        protect_segments = {"R"}  # R is never reduced

        for seg_id in reduction_order:
            if seg_id not in adjusted or deficit <= 0:
                continue
            if seg_id in protect_segments:
                continue  # Skip protected segments

            cfg = adjusted[seg_id]
            seg_cost = cfg.get("segment_cost", 0)
            if seg_cost <= 0:
                continue

            # How much can we reduce this segment?
            reduction = min(deficit, seg_cost * 0.3)  # Cut at most 30% per segment
            reduction_pct = (reduction / seg_cost) if seg_cost > 0 else 0

            # Reduce DCC (service level) for this segment
            dcc_reduction = reduction_pct * cfg["dcc_pct"]
            new_dcc = max(50.0, cfg["dcc_pct"] - dcc_reduction)
            cfg["dcc_pct"] = round(new_dcc, 1)

            # Reduce safety stock
            ss_reduction = reduction_pct * cfg["safety_stock_pct"]
            new_ss = max(5.0, cfg["safety_stock_pct"] - ss_reduction)
            cfg["safety_stock_pct"] = round(new_ss, 1)

            # Update segment cost
            cfg["segment_cost"] = round(seg_cost - reduction, 0)
            deficit -= reduction

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


def get_dept_ids_by_category(category_ids: List[int]) -> List[int]:
    """Load departments.json and return all dept IDs matching the given category IDs."""
    path = os.path.join(_BASE_DIR, "data", "departments.json")
    with open(path) as f:
        depts = json.load(f)
    return [d["id"] for d in depts if d["category_id"] in category_ids]


def optimize_policy(
    budget: float,
    service_target: float,
    dept_id: int,
    season: str = "Fall/Holiday",
    return_sku_level: bool = False
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
        return_sku_level: If True, return SKU-level configs instead of segment-level.

    Returns:
        Dict with 'feasible', 'minimum_budget', 'configs', 'achieved_service', etc.
    """
    dept_data = load_department_data(dept_id)
    segments_data = load_segments()

    # Step1: Compute minimum budget required for the target
    min_budget, min_configs = compute_min_budget(service_target, dept_data, segments_data)

    result = {
        "dept_id": dept_id,
        "dept_name": dept_data["department_name"],
        "budget": budget,
        "service_target": service_target,
        "season": season,
    }

    # Step2: Check feasibility
    if budget < min_budget * 0.95:  # 5% tolerance
        # INFEASIBLE — budget is insufficient
        achievable_service = estimate_achievable_service(
            budget, min_budget, service_target, segments_data
        )

        # Compute configs for the achievable service level
        achievable_configs = {}
        if achievable_service > 0:
            temp_min_budget, temp_configs = compute_min_budget(achievable_service, dept_data, segments_data)
            achievable_configs = adjust_configs_to_budget(temp_configs, budget, temp_min_budget, achievable_service, segments_data)

        result["feasible"] = False
        result["minimum_budget"] = min_budget
        result["achieved_service"] = achievable_service
        result["total_cost"] = round(sum(cfg.get("segment_cost", 0) for cfg in achievable_configs.values()), 0) if achievable_configs else 0
        result["options"] = [
            "increase_budget",
            "lower_target",
            "show_whats_possible"
        ]
        result["configs"] = achievable_configs  # Return achievable configs instead of None
        result["message"] = (
            f"Target: {service_target}% WIP with ${budget:,.0f} is not achievable. "
            f"Minimum budget required: ${min_budget:,.0f}. "
            f"With ${budget:,.0f}, you can achieve {achievable_service:.1f}% WIP."
        )
        return result

    # Step3: FEASIBLE — optimize within budget
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
    # Budget remaining
    budget_remaining = budget - total_cost
    result["budget_remaining"] = round(budget_remaining, 0)
    result["budget_remaining_millions"] = round(budget_remaining / 1_000_000, 1)
    # Risk quantification
    markdown_pct_sum = sum(cfg["end_of_season_pct"] for cfg in adjusted_configs.values())
    avg_markdown_pct = markdown_pct_sum / len(adjusted_configs) if adjusted_configs else 0.0
    result["markdown_risk"] = round(total_cost * avg_markdown_pct / 100.0, 0)
    if achieved < service_target:
        result["sales_loss_risk"] = round((service_target - achieved) * budget * 0.01, 0)
    else:
        result["sales_loss_risk"] = 0.0

    # Always include segment-level configs
    result["configs"] = adjusted_configs

    # If SKU-level requested, also compute per-SKU configs
    if return_sku_level:
        sku_configs = {}
        sku_clusters = dept_data.get("sku_clusters", [])
        for sku in sku_clusters:
            seg = sku.get("segment", "A")
            seg_def = next((s for s in segments_data["segments"] if s["id"] == seg), None)
            if not seg_def:
                continue
            # Per-SKU DCC (same as segment)
            sku_dcc = adjusted_configs.get(seg, {}).get("dcc_pct", 95.0)
            # Per-SKU safety stock
            lead_time = 6.0
            weekly_std = sku["demand_std"] / 4.0
            z_score = _inverse_normal_cdf(sku_dcc / 100.0)
            safety_units = z_score * math.sqrt(lead_time) * weekly_std
            safety_pct = (safety_units / max(sku["pog_capacity"], 1)) * 100.0
            # Per-SKU MOQ
            sku_moq = int(sku["demand_mean"] * 0.05)
            # Per-SKU cost
            sku_cost = (sku["demand_mean"] + safety_units) * sku["unit_cost"] * 1.15

            sku_configs[sku["cluster_id"]] = {
                "sku_name": sku["item_name"],
                "segment": seg,
                "dcc_pct": sku_dcc,
                "safety_stock_pct": round(safety_pct, 1),
                "reorder_point": int(sku["demand_mean"] * 0.15),
                "order_frequency_days": 7 if seg in ["A", "R"] else 14,
                "moq_threshold": sku_moq,
                "unit_cost": sku["unit_cost"],
                "estimated_cost": round(sku_cost, 0),
            }
        result["sku_configs"] = sku_configs

    result["message"] = (
        f"Target {service_target}% WIP achieved at ${budget:,.0f} budget. "
        f"Achieved service level: {achieved:.1f}%."
    )
    return result
