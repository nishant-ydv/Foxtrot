"""Foxtrot Streamlit Frontend — CBO-facing UI.

Features:
- Category → Department two-level selector (50 departments)
- Budget + service target input
- Unconstrained optimizer: shows feasibility alert + 3 options
- Policy config display (DCC, safety stock, allocation splits)
- Natural language scenario input + LLM narration
- High-stakes decision center
- Deployable to Streamlit Cloud for panel experimentation
"""
import streamlit as st
import requests
import json
from typing import Dict, Any, Optional

# Configuration
API_BASE_URL = "http://localhost:8000"

# Page config
st.set_page_config(
    page_title="Foxtrot — Inventory Policy Optimizer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


# --- Helper functions ---

@st.cache_data(ttl=3600)
def load_departments():
    """Load departments from backend API."""
    try:
        response = requests.get(f"{API_BASE_URL}/departments", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to load departments: {e}")
        return None


def cal_optimize(budget: float, target: float, dept_id: int, season: str):
    """Call POST /optimize endpoint."""
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
    """Call POST /scenario endpoint."""
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
    """Call POST /decision endpoint."""
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
    st.error("Failed to load department data. Is the backend running at " + API_BASE_URL + "?")
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
                # Update budget to minimum
                budget = result.get("minimum_budget", budget)
                st.rerun()

        with opt_col2:
            if st.button("2. Keep & Show", use_container_width=True):
                # Show what's possible with current budget
                if result.get("configs"):
                    st.session_state.optimize_result["feasible"] = True
                    st.rerun()

        with opt_col3:
            if st.button("3. Lower Target", use_container_width=True):
                # Lower target to achievable level
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
            # Create a table
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
