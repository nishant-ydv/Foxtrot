"""Foxtrot Streamlit Frontend — CBO-facing UI.

Features:
- Category → Department two-level selector (50 departments)
- Budget + service target input
- Unconstrained optimizer: shows feasibility alert + 3 options
- Policy config display (DCC, safety stock, allocation splits)
- Natural language scenario input + LLM narration
- High-stakes decision center
- Deployable to Streamlit Cloud (standalone mode, no backend needed)
"""
import streamlit as st
import json
import os
import sys
from typing import Dict, Any, Optional

# --- Standalone mode: import backend modules directly ---
# Add backend directory to path so we can import optimizer and llm_layer
backend_path = os.path.join(os.path.dirname(__file__), "..", "backend")
backend_path = os.path.abspath(backend_path)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

try:
    from optimizer import optimize_policy
    from llm_layer import parse_scenario, narrate_tradeoff, frame_decision, explain_infeasibility
    STANDALONE = True
except ImportError:
    # Fall back to API mode if modules can't be imported
    import requests
    STANDALONE = False
    API_BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Page config
st.set_page_config(
    page_title="Foxtrot — Inventory Policy Optimizer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.sidebar.caption(f"{'Standalone' if STANDALONE else 'API'} mode")


# --- Helper functions ---

@st.cache_data(ttl=3600)
def load_departments():
    """Load departments from backend data files (standalone) or API."""
    if STANDALONE:
        try:
            import models
            with open(os.path.join(backend_path, "data", "categories.json")) as f:
                categories_data = json.load(f)
            with open(os.path.join(backend_path, "data", "departments.json")) as f:
                departments_data = json.load(f)
            categories = [models.CategoryInfo(id=c["id"], name=c["name"]) for c in categories_data]
            departments = [
                models.DepartmentInfo(id=d["id"], name=d["name"], category_id=d["category_id"])
                for d in departments_data
            ]
            return {"categories": [c.model_dump() for c in categories],
                    "departments": [d.model_dump() for d in departments]}
        except Exception as e:
            st.error(f"Failed to load departments: {e}")
            return None
    else:
        try:
            response = requests.get(f"{API_BASE_URL}/departments", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Failed to load departments: {e}")
            return None


def cal_optimize(budget: float, target: float, dept_id: int, season: str):
    """Run optimization (standalone or API mode)."""
    if STANDALONE:
        try:
            result = optimize_policy(budget, target, dept_id, season)
            # Convert to same format as API response
            from models import PolicyConfig
            configs_response = None
            if result.get("configs"):
                configs_response = {}
                for seg_id, cfg in result["configs"].items():
                    configs_response[seg_id] = {k: v for k, v in cfg.items() if k in [
                        "segment", "dcc_pct", "safety_stock_pct", "reorder_point",
                        "order_frequency_days", "moq_threshold", "preseason_allocation_pct",
                        "inseason_allocation_pct", "markdown_reserve_pct"
                    ]}
            return {
                "feasible": result["feasible"],
                "minimum_budget": result.get("minimum_budget"),
                "achieved_service": result.get("achieved_service"),
                "total_cost": result.get("total_cost"),
                "configs": configs_response,
                "options": result.get("options"),
                "narration": result.get("narration"),
                "dept_id": result.get("dept_id"),
                "dept_name": result.get("dept_name")
            }
        except Exception as e:
            return {"feasible": False, "message": f"Optimization failed: {e}"}
    else:
        try:
            response = requests.post(
                f"{API_BASE_URL}/optimize",
                json={"budget": budget, "service_target": target, "dept_id": dept_id, "season": season},
                timeout=30
            )
            return response.json()
        except Exception as e:
            return {"feasible": False, "message": f"API call failed: {e}"}


def cal_scenario(nl_input: str, current_policy: Dict, budget: float, target: float, dept_id: int):
    """Run scenario (standalone or API mode)."""
    if STANDALONE:
        try:
            llm_response = parse_scenario(
                nl_input=nl_input,
                current_policy=current_policy,
                budget=budget,
                service_target=target
            )
            if llm_response.get("error"):
                return {
                    "feasible": True,
                    "narration": f"Scenario '{nl_input}' noted. LLM narration unavailable.",
                    "budget_change": 0.0,
                    "service_change": 0.0
                }
            # Adjust budget/target based on parsed action
            new_budget = budget
            new_target = target
            action = llm_response.get("action", "unknown")
            value = llm_response.get("value", 0)
            if action == "reduce_budget":
                new_budget = max(0, budget - abs(value))
            elif action == "increase_budget":
                new_budget = budget + abs(value)
            elif action == "reduce_target":
                new_target = max(50.0, target - abs(value))
            elif action == "increase_target":
                new_target = min(99.9, target + abs(value))

            new_result = optimize_policy(new_budget, new_target, dept_id)
            narration = narrate_tradeoff(
                old_policy={"service": target, "configs": current_policy},
                new_policy=new_result,
                budget_change=new_budget - budget,
                service_change=new_result.get("achieved_service", 0) - target
            )
            configs_response = None
            if new_result.get("feasible") and new_result.get("configs"):
                configs_response = {seg_id: {k: v for k, v in cfg.items() if k in [
                    "segment", "dcc_pct", "safety_stock_pct", "reorder_point",
                    "order_frequency_days", "moq_threshold", "preseason_allocation_pct",
                    "inseason_allocation_pct", "markdown_reserve_pct"
                ]} for seg_id, cfg in new_result["configs"].items()}
            return {
                "feasible": new_result["feasible"],
                "configs": configs_response,
                "narration": narration,
                "budget_change": new_budget - budget,
                "service_change": new_result.get("achieved_service", 0) - target
            }
        except Exception as e:
            return {"feasible": False, "narration": f"Scenario failed: {e}",
                    "budget_change": 0.0, "service_change": 0.0}
    else:
        try:
            response = requests.post(
                f"{API_BASE_URL}/scenario",
                json={
                    "nl_input": nl_input,
                    "current_policy": current_policy,
                    "budget": budget,
                    "service_target": target,
                    "dept_id": dept_id
                },
                timeout=30
            )
            return response.json()
        except Exception as e:
            return {"feasible": False, "narration": f"Scenario failed: {e}"}


def cal_decision(context: str, dept_id: int, budget: float, service: float):
    """Frame decision (standalone or API mode)."""
    if STANDALONE:
        try:
            llm_response = frame_decision(
                decision_context=context,
                dept_id=dept_id,
                budget=budget,
                current_service=service
            )
            return {
                "context": context,
                "options": llm_response.get("options", []),
                "recommendation": llm_response.get("recommendation", "Unknown")
            }
        except Exception as e:
            return {
                "context": context,
                "options": [
                    {
                        "option": "Chase demand",
                        "description": "Place additional POs to meet the forecast surge",
                        "upside": budget * 0.02,
                        "downside": -budget * 0.03,
                        "recommendation": True
                    },
                    {
                        "option": "Hold course",
                        "description": "Accept the miss, avoid additional inventory risk",
                        "upside": 0,
                        "downside": -budget * 0.05,
                        "recommendation": False
                    }
                ],
                "recommendation": "Chase demand",
                "note": f"LLM unavailable: {str(e)}"
            }
    else:
        try:
            response = requests.post(
                f"{API_BASE_URL}/decision",
                json={
                    "decision_context": context,
                    "dept_id": dept_id,
                    "budget": budget,
                    "current_service": service
                },
                timeout=30
            )
            return response.json()
        except Exception as e:
            return {"context": context, "options": [], "recommendation": f"Error: {e}"}


# --- Sidebar: Inputs ---

st.sidebar.title("📊 Foxtrot")
st.sidebar.caption("AI-Powered Inventory Policy Optimizer")

# Load departments
dept_data = load_departments()

if dept_data:
    # Category selector
    categories = {c["id"]: c["name"] for c in dept_data["categories"]}
    category_names = list(categories.values())

    selected_category_name = st.sidebar.selectbox(
        "Category",
        category_names,
        index=0
    )

    # Find category ID
    selected_category_id = None
    for c in dept_data["categories"]:
        if c["name"] == selected_category_name:
            selected_category_id = c["id"]
            break

    # Department selector (filtered by category)
    filtered_depts = [
        d for d in dept_data["departments"]
        if d["category_id"] == selected_category_id
    ]

    dept_options = {f"Dept {d['id']} — {d['name']}": d["id"] for d in filtered_depts}

    selected_dept_label = st.sidebar.selectbox(
        "Department",
        list(dept_options.keys()),
        index=0
    )
    selected_dept_id = dept_options[selected_dept_label]

    # Get department name for display
    dept_name = selected_dept_label.split(" — ", 1)[1] if " — " in selected_dept_label else ""

    st.sidebar.markdown("---")

    # Budget input
    budget = st.sidebar.number_input(
        "Budget ($)",
        min_value=1000000.0,
        max_value=500000000.0,
        value=100000000.0,  # $100M default
        step=1000000.0,
        format="%.0f"
    )

    # Service target
    service_target = st.sidebar.slider(
        "Service Target (%)",
        min_value=80.0,
        max_value=99.0,
        value=97.0,
        step=0.5
    )

    # Season
    season = st.sidebar.selectbox(
        "Season",
        ["Fall/Holiday", "Spring/Summer", "Back to School", "Year Round"],
        index=0
    )

    st.sidebar.markdown("---")

    # Optimize button
    optimize_clicked = st.sidebar.button("🚀 Optimize Policy", use_container_width=True, type="primary")

else:
    st.error("Failed to load department data.")
    st.stop()


# --- Main content ---

st.title("📊 Foxtrot — Inventory Policy Optimizer")
st.caption(f"Department: {dept_name} (ID: {selected_dept_id})  |  Category: {selected_category_name}")

# Initialize session state
if "optimize_result" not in st.session_state:
    st.session_state.optimize_result = None
if "current_policy" not in st.session_state:
    st.session_state.current_policy = None

# --- Optimization Result ---

if optimize_clicked:
    with st.spinner("Optimizing policy..."):
        result = cal_optimize(budget, service_target, selected_dept_id, season)
        st.session_state.optimize_result = result
        st.session_state.current_policy = result.get("configs")

# Display optimization result
result = st.session_state.get("optimize_result")

if result:
    if not result.get("feasible"):
        # INFEASIBILITY ALERT — Key feature
        st.error("⚠️ Budget Insufficient")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Target Service", f"{service_target}%")
            st.metric("Your Budget", f"${budget:,.0f}")

        with col2:
            min_budget = result.get("minimum_budget", 0)
            st.metric("Minimum Required", f"${min_budget:,.0f}")
            st.metric("Budget Gap", f"${min_budget - budget:,.0f}")

        with col3:
            achieved = result.get("achieved_service", 0)
            st.metric("Achievable Service", f"{achieved:.1f}%")
            st.metric("Service Gap", f"{service_target - achieved:.1f} pts")

        st.warning(result.get("message", "Budget is insufficient for target."))

        # Three options
        st.subheader("Your Options")

        opt_col1, opt_col2, opt_col3 = st.columns(3)

        with opt_col1:
            if st.button("1. Increase Budget", use_container_width=True):
                budget = result.get("minimum_budget", budget)
                st.rerun()

        with opt_col2:
            if st.button("2. Keep & Show", use_container_width=True):
                if result.get("configs"):
                    st.session_state.optimize_result["feasible"] = True
                    st.rerun()

        with opt_col3:
            if st.button("3. Lower Target", use_container_width=True):
                new_target = result.get("achieved_service", service_target - 3.0)
                st.rerun()

    else:
        # FEASIBLE — Show policy configs
        st.success(f"✅ Target {service_target}% WIP achieved at ${budget:,.0f}")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Achieved Service", f"{result.get('achieved_service', 0):.1f}%")
        with col2:
            st.metric("Total Cost", f"${result.get('total_cost', 0):,.0f}")
        with col3:
            st.metric("Budget Remaining", f"${budget - result.get('total_cost', 0):,.0f}")

        # Policy configs per segment
        st.subheader("Policy Configurations by Segment")

        configs = result.get("configs", {})
        if configs:
            import pandas as pd

            rows = []
            for seg_id, cfg in configs.items():
                rows.append({
                    "Segment": seg_id,
                    "DCC (%)": cfg.get("dcc_pct", 0),
                    "Safety Stock (%)": cfg.get("safety_stock_pct", 0),
                    "Reorder Point": cfg.get("reorder_point", 0),
                    "Order Freq (days)": cfg.get("order_frequency_days", 0),
                    "MOQ Threshold": cfg.get("moq_threshold", 0),
                    "Pre-Season %": cfg.get("preseason_allocation_pct", 0),
                    "In-Season %": cfg.get("inseason_allocation_pct", 0),
                    "Markdown %": cfg.get("markdown_reserve_pct", 0),
                    "Segment Cost": f"${cfg.get('segment_cost', 0):,.0f}"
                })

            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Bar chart: DCC by segment
            chart_data = pd.DataFrame({
                "Segment": [r["Segment"] for r in rows],
                "DCC (%)": [r["DCC (%)"] for r in rows],
                "Safety Stock (%)": [r["Safety Stock (%)"] for r in rows]
            })
            st.bar_chart(chart_data.set_index("Segment"))

        # LLM narration
        narration = result.get("narration")
        if narration:
            st.info(f"**LLM Analysis:** {narration}")

# --- Scenario Explorer ---

st.markdown("---")
st.subheader("🔮 Scenario Explorer")
st.caption("Type a natural language scenario to see instant policy changes with trade-off narration.")

scenario_input = st.text_input(
    "What-if Scenario",
    placeholder="e.g., What if budget drops $3M? What if lead time doubles for vendor X?",
    key="scenario_input"
)

if st.button("Run Scenario", use_container_width=True) and scenario_input:
    if not st.session_state.current_policy:
        st.warning("Please run Optimize first to get a baseline policy.")
    else:
        with st.spinner("Running scenario..."):
            scenario_result = cal_scenario(
                nl_input=scenario_input,
                current_policy=st.session_state.current_policy,
                budget=budget,
                target=service_target,
                dept_id=selected_dept_id
            )

            if scenario_result.get("narration"):
                st.success("**Scenario Results:**")
                st.write(scenario_result["narration"])

                if scenario_result.get("configs"):
                    st.session_state.current_policy = scenario_result["configs"]
                    st.rerun()
            else:
                st.error("Scenario failed. Please try again.")

# --- Decision Center ---

st.markdown("---")
st.subheader("⚡ High-Stakes Decision Center")
st.caption("AI-powered decision framing with quantified trade-offs for mid-season decisions.")

decision_context = st.text_area(
    "Decision Context",
    placeholder="e.g., Underforecasted holiday by 20% for Product X, 1 week left. Do we place POs?",
    key="decision_context"
)

if st.button("Frame Decision", use_container_width=True) and decision_context:
    with st.spinner("Framing decision..."):
        current_service = result.get("achieved_service", service_target) if result else service_target
        decision_result = cal_decision(
            context=decision_context,
            dept_id=selected_dept_id,
            budget=budget,
            service=current_service
        )

        st.write(f"**Context:** {decision_result.get('context', '')}")
        st.write("**Options:**")

        for opt in decision_result.get("options", []):
            rec = "✅ " if opt.get("recommendation") else ""
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"{rec}**{opt.get('option', '')}**")
                st.write(opt.get("description", ""))
                upside = opt.get("upside")
                downside = opt.get("downside")
                if upside is not None:
                    st.write(f"Upside: ${upside:,.0f}  |  Downside: ${abs(downside or 0):,.0f}")
            with col2:
                if st.button("Select", key=f"select_{opt.get('option', '')}"):
                    st.success(f"Selected: {opt.get('option')}")

        st.info(f"**Recommendation:** {decision_result.get('recommendation', '')}")

# --- Footer ---

st.markdown("---")
st.caption(
    "Foxtrot V0 — AI-Powered Inventory Policy Optimizer  |  "
    "Built for CBOs who want to explore 20+ scenarios in the time it takes to do 2 in Excel."
)
