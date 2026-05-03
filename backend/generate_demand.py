#!/usr/bin/env python3
"""Generate demand forecast JSON files for all 50 departments."""
import json
import random
import os

# Load departments
with open("data/departments.json") as f:
    departments = json.load(f)

# Load segments for default values
with open("data/segments.json") as f:
    segments_data = json.load(f)

seg_defaults = {s["id"]: s for s in segments_data["segments"]}

# Category season profiles
season_profiles = {
    1: {"name": "Fall/Holiday", "preseason_pct": 55.0, "inseason_pct": 35.0, "markdown_pct": 10.0},
    2: {"name": "Fall/Holiday", "preseason_pct": 25.0, "inseason_pct": 65.0, "markdown_pct": 10.0},
    3: {"name": "Fall/Holiday", "preseason_pct": 30.0, "inseason_pct": 60.0, "markdown_pct": 10.0},
    4: {"name": "Fall/Holiday", "preseason_pct": 20.0, "inseason_pct": 70.0, "markdown_pct": 10.0},
    5: {"name": "Fall/Holiday", "preseason_pct": 30.0, "inseason_pct": 60.0, "markdown_pct": 10.0},
    6: {"name": "Fall/Holiday", "preseason_pct": 50.0, "inseason_pct": 40.0, "markdown_pct": 10.0},
    7: {"name": "Fall/Holiday", "preseason_pct": 40.0, "inseason_pct": 50.0, "markdown_pct": 10.0},
    8: {"name": "Fall/Holiday", "preseason_pct": 45.0, "inseason_pct": 40.0, "markdown_pct": 15.0},
    9: {"name": "Fall/Holiday", "preseason_pct": 25.0, "inseason_pct": 65.0, "markdown_pct": 10.0},
    10: {"name": "Fall/Holiday", "preseason_pct": 20.0, "inseason_pct": 70.0, "markdown_pct": 10.0},
}

# Segment SKU templates — $100M-scale departments
# target total_demand_value ≈ $80-120M per department
segment_templates = {
    "A": {"count": 2, "demand_range": (80000, 150000), "std_pct": 0.15, "cost_range": (50, 120), "margin_range": (40, 50), "pog_range": (30000, 60000)},
    "B": {"count": 2, "demand_range": (40000, 80000), "std_pct": 0.20, "cost_range": (30, 100), "margin_range": (40, 55), "pog_range": (20000, 40000)},
    "C": {"count": 2, "demand_range": (15000, 40000), "std_pct": 0.30, "cost_range": (15, 40), "margin_range": (50, 65), "pog_range": (10000, 25000)},
    "R": {"count": 2, "demand_range": (25000, 60000), "std_pct": 0.12, "cost_range": (20, 130), "margin_range": (35, 55), "pog_range": (10000, 25000)},
}

def generate_department_demand(dept):
    """Generate demand data for a single department."""
    cat_id = dept["category_id"]
    profile = season_profiles.get(cat_id, season_profiles[1])

    sku_clusters = []
    total_demand_value = 0.0
    cluster_num = 0

    for seg_id, template in segment_templates.items():
        defaults = seg_defaults[seg_id]
        for i in range(template["count"]):
            cluster_num += 1
            demand_mean = random.uniform(*template["demand_range"])
            demand_std = demand_mean * template["std_pct"]
            unit_cost = random.uniform(*template["cost_range"])
            margin_pct = random.uniform(*template["margin_range"])
            pog_capacity = random.uniform(*template["pog_range"])

            sku_clusters.append({
                "cluster_id": f"{dept['name'][:2].upper()}_{seg_id}_{cluster_num:03d}",
                "segment": seg_id,
                "item_name": f"{dept['name']} - {seg_id} Item {cluster_num}",
                "demand_mean": round(demand_mean, 0),
                "demand_std": round(demand_std, 0),
                "unit_cost": round(unit_cost, 2),
                "margin_pct": round(margin_pct, 1),
                "pog_capacity": round(pog_capacity, 0)
            })
            total_demand_value += demand_mean * unit_cost

    # Calculate budget needed (roughly 60% of total demand value for inventory)
    total_budget_needed = total_demand_value * random.uniform(0.8, 1.2)

    return {
        "department_id": dept["id"],
        "department_name": dept["name"],
        "season": profile,
        "sku_clusters": sku_clusters,
        "total_demand_value": round(total_demand_value, 0),
        "total_budget_needed": round(total_budget_needed, 0)
    }

def main():
    random.seed(42)  # Reproducible
    os.makedirs("data/demand", exist_ok=True)

    for dept in departments:
        demand_data = generate_department_demand(dept)
        filepath = f"data/demand/dept_{dept['id']}.json"
        with open(filepath, "w") as f:
            json.dump(demand_data, f, indent=2)
        print(f"Created {filepath}")

    print(f"\nGenerated demand files for {len(departments)} departments.")

if __name__ == "__main__":
    main()
