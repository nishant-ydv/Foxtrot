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
from dotenv import load_dotenv

# Load API keys into os.environ BEFORE backend imports
# 1. Try .env file (local development)
_env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.exists(_env_path):
    load_dotenv(_env_path, override=True)

# 2. Try Streamlit secrets (Streamlit Cloud deployment)
try:
    _secrets = st.secrets
    # Map secret keys to environment variables
    _key_map = {
        "ANTHROPIC_API_KEY": ["anthropic_api_key", "ANTHROPIC_API_KEY"],
        "ANTHROPIC_BASE_URL": ["anthropic_base_url", "ANTHROPIC_BASE_URL"],
        "ANTHROPIC_MODEL": ["anthropic_model", "ANTHROPIC_MODEL"],
        "ANTHROPIC_FALLBACK_MODEL": ["anthropic_fallback_model", "ANTHROPIC_FALLBACK_MODEL"],
    }
    for env_key, secret_keys in _key_map.items():
        for sk in secret_keys:
            if sk in _secrets:
                os.environ[env_key] = str(_secrets[sk]).strip()
                break
except Exception:
    pass  # Not on Streamlit Cloud or secrets not configured

# --- Standalone mode: import backend modules directly ---
# Add backend directory to path so we can import optimizer and llm_layer
backend_path = os.path.join(os.path.dirname(__file__), "..", "backend")
backend_path = os.path.abspath(backend_path)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

try:
    # Try OR-Tools optimizer first
    from optimizer import optimize_policy
    from llm_layer import parse_scenario, narrate_tradeoff, frame_decision, explain_infeasibility
    STANDALONE = True
except ImportError:
    # Try simple optimizer (no OR-Tools needed)
    try:
        from optimizer_simple import optimize_policy
        from llm_layer import parse_scenario, narrate_tradeoff, frame_decision, explain_infeasibility
        STANDALONE = True
    except ImportError:
        # Fall back to API mode
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

# --- Onboarding for first-time users ---
if "show_onboarding" not in st.session_state:
    st.session_state.show_onboarding = True

if st.session_state.show_onboarding:
    with st.container():
        st.info("**🚀 Quick Start Guide**  (dismissible)")
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown("""
            1. **Select** Department/Category in the sidebar
            2. **Set** Budget ($M) and Service Target (%)
            3. **Click** "🚀 Optimize Policy"
            4. **Explore** scenarios by typing natural language below
            """)
        with col2:
            if st.button("Got it ✓", key="dismiss_onboarding"):
                st.session_state.show_onboarding = False
                st.rerun()

st.markdown("---")

# --- Helper functions ---

def format_currency(amount: float) -> str:
    """Format amount as $M, $K, or raw $ based on magnitude."""
    if amount is None:
        amount = 0
    if amount >= 1_000_000:
        return f"${amount/1_000_000:.1f}M"
    elif amount >= 1_000:
        return f"${amount/1_000:.1f}K"
    else:
        return f"${amount:,.0f}"

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


def cal_optimize(budget: float, target: float, dept_id: int, season: str, dept_ids: list = None, return_sku_level: bool = False):
    """Run optimization (standalone or API mode). Handles single or multiple dept IDs."""
    if STANDALONE:
        # Standalone mode: use first dept if multiple selected (multi-dept optimization coming soon)
        if dept_ids and len(dept_ids) > 1:
            st.warning("Multi-department optimization in standalone mode coming soon. Using first selected department.")
            dept_id = dept_ids[0]
        try:
            # Always request SKU-level data so it's available for "Keep & Show"
            result = optimize_policy(budget, target, dept_id, season, return_sku_level=True)
            # Convert to same format as API response
            from models import PolicyConfig
            configs_response = None
            if result.get("configs"):
                configs_response = {}
                for seg_id, cfg in result["configs"].items():
                    configs_response[seg_id] = {k: v for k, v in cfg.items() if k in [
                        "segment", "dcc_pct", "safety_stock_pct", "reorder_point",
                        "order_frequency_days", "moq_threshold", "preseason_allocation_pct",
                        "inseason_allocation_pct", "end_of_season_pct", "segment_cost"
                    ]}
            return {
                "feasible": result["feasible"],
                "minimum_budget": result.get("minimum_budget"),
                "service_target": target,
                "achieved_service": result.get("achieved_service"),
                "total_cost": result.get("total_cost"),
                "configs": configs_response,
                "sku_configs": result.get("sku_configs"),
                "options": result.get("options"),
                "narration": result.get("narration"),
                "dept_id": result.get("dept_id"),
                "dept_name": result.get("dept_name")
            }
        except Exception as e:
            return {"feasible": False, "message": f"Optimization failed: {e}"}
    else:
        # API mode: pass dept_ids if available, else single dept_id
        payload = {"budget": budget, "service_target": target, "season": season, "return_sku_level": return_sku_level}
        if dept_ids and len(dept_ids) > 1:
            payload["dept_ids"] = dept_ids
        else:
            payload["dept_id"] = dept_id
        try:
            response = requests.post(
                f"{API_BASE_URL}/optimize",
                json=payload,
                timeout=30
            )
            return response.json()
        except Exception as e:
            return {"feasible": False, "message": f"API call failed: {e}"}


def cal_scenario(nl_input: str, current_policy: Dict, budget: float, target: float, dept_id: int, dept_ids: list = None):
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

            # Use first dept if multiple selected (multi-dept scenario coming soon)
            scenario_dept_id = dept_ids[0] if dept_ids and len(dept_ids) > 1 else dept_id
            new_result = optimize_policy(new_budget, new_target, scenario_dept_id)
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
                    "inseason_allocation_pct", "end_of_season_pct"
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


def cal_decision(context: str, dept_id: int, budget: float, service: float, dept_ids: list = None):
    """Frame decision (standalone or API mode)."""
    if STANDALONE:
        try:
            # Use first dept if multiple selected
            decision_dept_id = dept_ids[0] if dept_ids and len(dept_ids) > 1 else dept_id
            llm_response = frame_decision(
                decision_context=context,
                dept_id=decision_dept_id,
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
                        "recommendation": True,
                        "explanation": f"Chase: Increase purchasing mid-season to meet targets despite forecast errors. Upside: +${budget*0.02/1_000_000:.1f}M sales uplift (~2% revenue capture), Downside: -${budget*0.03/1_000_000:.1f}M potential sales loss. PO volume: ~${budget*0.02:,.0f} in additional orders."
                    },
                    {
                        "option": "Hold course",
                        "description": "Accept the miss, avoid additional inventory risk",
                        "upside": 0,
                        "downside": -budget * 0.05,
                        "recommendation": False,
                        "explanation": f"Hold: Accept the mid-season miss and adjust targets. Downside: -${budget*0.05/1_000_000:.1f}M potential sales loss (~5% of budget at risk). No additional PO volume."
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

st.sidebar.title("Foxtrot")
st.sidebar.caption("AI-Powered Inventory Policy Optimizer")

# Load departments
dept_data = load_departments()

if dept_data:
    # Category selector (multi-select)
    categories = {c["id"]: c["name"] for c in dept_data["categories"]}
    category_names = list(categories.values())

    selected_category_names = st.sidebar.multiselect(
        "Categories",
        category_names,
        default=[category_names[0]] if category_names else [],
        help="Select one or more categories to filter departments. Each category maps to a group of departments."
    )

    # Find selected category IDs
    selected_category_ids = []
    for c in dept_data["categories"]:
        if c["name"] in selected_category_names:
            selected_category_ids.append(c["id"])

    # Department selector (multi-select, filtered by selected categories)
    filtered_depts = [
        d for d in dept_data["departments"]
        if d["category_id"] in selected_category_ids
    ]

    dept_options = {f"Dept {d['id']} — {d['name']}": d["id"] for d in filtered_depts}
    dept_labels = list(dept_options.keys())

    selected_dept_labels = st.sidebar.multiselect(
        "Departments",
        dept_labels,
        default=[dept_labels[0]] if dept_labels else [],
        help="Select one or more departments to optimize. Multi-department mode aggregates results across all selected."
    )
    selected_dept_ids = [dept_options[label] for label in selected_dept_labels]

    # Get department names for display
    dept_names = [label.split(" — ", 1)[1] if " — " in label else "" for label in selected_dept_labels]
    dept_name = ", ".join(dept_names) if dept_names else "None"
    selected_dept_id = selected_dept_ids[0] if selected_dept_ids else None  # For single-dept fallback

    st.sidebar.markdown("---")

    # Budget input (entered in $M, stored in dollars internally)
    if "budget_m" not in st.session_state:
        st.session_state.budget_m = 100.0  # Default $100M

    budget_m = st.sidebar.number_input(
        "Budget ($M)",
        min_value=1.0,
        max_value=500.0,
        value=st.session_state.budget_m,
        step=1.0,
        format="%.1f",
        help="Budget in millions of dollars. This is the total Open-to-Buy (OTB) for the season."
    )
    # Update session state if user changes the input
    budget = budget_m * 1_000_000  # Convert to dollars for internal use

    # Service target: slider + number input
    st.sidebar.markdown("**Service Target (%)**")
    if "service_target" not in st.session_state:
        st.session_state.service_target = 97.0

    # Callbacks to sync slider <-> number_input
    def _on_slider_change():
        st.session_state.service_target = st.session_state.service_slider
        st.session_state.service_input = st.session_state.service_slider

    def _on_input_change():
        st.session_state.service_target = st.session_state.service_input
        st.session_state.service_slider = st.session_state.service_input

    service_col1, service_col2 = st.sidebar.columns([3, 1])
    with service_col1:
        st.slider(
            "Service Slider",
            min_value=50.0,
            max_value=99.0,
            value=st.session_state.service_target,
            step=0.5,
            key="service_slider",
            help="Target service level (% of time items are in stock). 97% = premium, 90% = standard, 80% = budget.",
            label_visibility="collapsed",
            on_change=_on_slider_change
        )

    with service_col2:
        st.number_input(
            "Service Input",
            min_value=50.0,
            max_value=99.0,
            value=st.session_state.service_target,
            step=0.5,
            key="service_input",
            label_visibility="collapsed",
            on_change=_on_input_change
        )

    # Read the authoritative value
    service_target = st.session_state.service_target

    # Season
    season = st.sidebar.selectbox(
        "Season",
        ["Fall/Holiday", "Spring/Summer", "Back to School", "Year Round"],
        index=0,
        help="Season determines demand patterns. Fall/Holiday has highest volume, Spring/Summer is moderate."
    )

    # SKU-level policy toggle
    sku_view = st.sidebar.checkbox(
        "Show SKU-level policy",
        key="sku_view",
        help="When checked, shows policy configs for individual SKUs instead of segment-level aggregates. Requires more computation."
    )

    st.sidebar.markdown("---")

    # Optimize button
    optimize_clicked = st.sidebar.button("🚀 Optimize Policy", width='stretch', type="primary")

else:
    st.error("Failed to load department data.")
    st.stop()


# --- Main content ---

st.title("Foxtrot — Inventory Policy Optimizer")
st.caption(f"Department: {dept_name} (ID: {selected_dept_id})  |  Category: {', '.join(selected_category_names) if selected_category_names else 'None'}")

# Initialize session state
if "optimize_result" not in st.session_state:
    st.session_state.optimize_result = None
if "current_policy" not in st.session_state:
    st.session_state.current_policy = None
if "selected_decision" not in st.session_state:
    st.session_state.selected_decision = None

# --- Optimization Result ---

if optimize_clicked:
    with st.spinner("Optimizing policy..."):
        result = cal_optimize(budget, service_target, selected_dept_id, season, dept_ids=selected_dept_ids, return_sku_level=sku_view)
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
            st.metric("Your Budget", format_currency(budget))

        with col2:
            min_budget = result.get("minimum_budget", 0)
            st.metric("Minimum Required", format_currency(min_budget))
            st.metric("Budget Gap", format_currency(min_budget - budget))

        with col3:
            achieved = result.get("achieved_service", 0)
            st.metric("Achievable Service", f"{achieved:.1f}%")
            st.metric("Service Gap", f"{service_target - achieved:.1f} pts")

        st.warning(result.get("message", "Budget is insufficient for target."))

        # Three options
        st.subheader("Your Options")

        opt_col1, opt_col2, opt_col3 = st.columns(3)

        with opt_col1:
            if st.button("1. Increase Budget", width='stretch'):
                min_budget = result.get("minimum_budget", budget)
                st.session_state.budget_m = min_budget / 1_000_000  # Convert $M
                st.rerun()

        with opt_col2:
            if st.button("2. Keep & Show", width='stretch'):
                # Show achievable configs even though target isn't fully met
                if st.session_state.optimize_result:
                    st.session_state.optimize_result["feasible"] = True
                    st.rerun()

        with opt_col3:
            if st.button("3. Lower Target", width='stretch'):
                new_target = max(result.get("achieved_service", service_target - 3.0), 50.0)
                st.session_state.service_target = new_target
                st.rerun()

    else:
        # FEASIBLE or Keep & Show — Show policy configs
        achieved = result.get("achieved_service", 0)
        target = result.get("service_target") or service_target
        total_cost = result.get("total_cost") or 0

        # If total_cost is still 0, compute from segment configs (segment_cost key)
        if not total_cost:
            seg_configs = result.get("configs", {})
            total_cost = round(sum(cfg.get("segment_cost", 0) for cfg in seg_configs.values()), 0)

        # Cap total_cost at budget for display (can't spend more than budget)
        display_cost = min(total_cost, budget)
        budget_remaining = max(budget - total_cost, 0)

        if achieved >= target:
            st.success(f"✅ Target {target}% WIP achieved at {format_currency(budget)}")
        else:
            st.warning(f"⚠️ {achieved:.1f}% service achieved with {format_currency(budget)} — target was {target}%")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Achieved Service", f"{achieved:.1f}%")
        with col2:
            st.metric("Total Cost", format_currency(display_cost))
        with col3:
            st.metric("Budget Remaining", format_currency(budget_remaining))
        # Policy configs per segment
        st.subheader("Policy Configurations by Segment")

        import pandas as pd

        # Always show segment-level table
        configs = result.get("configs", {})
        if configs:
            rows = []
            for seg_id, cfg in configs.items():
                rows.append({
                    "Segment": seg_id,
                    "DCC (%)": cfg.get("dcc_pct", 0),
                    "Safety Stock (%)": cfg.get("safety_stock_pct", 0),
                    "Order Freq (days)": cfg.get("order_frequency_days", 0),
                    "MOQ Threshold": cfg.get("moq_threshold", 0),
                    "Pre-Season %": cfg.get("preseason_allocation_pct", 0),
                    "In-Season %": cfg.get("inseason_allocation_pct", 0),
                    "End of Season %": cfg.get("end_of_season_pct", 0),
                })

            df = pd.DataFrame(rows)
            st.dataframe(df, width='stretch', hide_index=True)

        # SKU-level table (shown when checkbox is ticked)
        sku_configs = result.get("sku_configs", {})
        if sku_configs:
            st.subheader("SKU-Level Policy Details")
            sku_rows = []
            for sku_id, cfg in sku_configs.items():
                sku_rows.append({
                    "SKU ID": sku_id,
                    "Name": cfg.get("sku_name", ""),
                    "Segment": cfg.get("segment", ""),
                    "DCC (%)": cfg.get("dcc_pct", 0),
                    "Safety Stock (%)": cfg.get("safety_stock_pct", 0),
                    "Reorder Point": cfg.get("reorder_point", 0),
                    "MOQ Threshold": cfg.get("moq_threshold", 0),
                    "Unit Cost ($)": cfg.get("unit_cost", 0),
                    "Est. Cost ($)": cfg.get("estimated_cost", 0),
                })
            sku_df = pd.DataFrame(sku_rows)
            st.dataframe(sku_df, width='stretch', hide_index=True)
        elif sku_view and not sku_configs:
            st.info("SKU-level data is only available when 'Show SKU-level policy' is checked before clicking Optimize.")

        # LLM narration
        narration = result.get("narration")
        if narration:
            st.info(f"**LLM Analysis:** {narration}")


st.markdown("---")
# How to Read Results — expandable guide
with st.expander("ℹ️ How to Read Optimization Results"):
    st.markdown("""
    **Feasibility Indicators:**
    - ✅ **Feasible** (green) = Target is achievable within budget
    - ⚠️ **Infeasible** (red) = Budget insufficient, see options below

    **Key Metrics:**
    - **Total Cost** = Inventory investment needed for the policy
    - **Budget Remaining** = Unused budget (shown in $M for readability)
    - **Achieved Service** = Actual in-stock % the policy delivers

    **Risk Quantification:**
    - **Markdown Risk** = Potential loss from end-of-season markdowns (~10% of cost)
    - **Sales Loss Risk** = Potential loss if achieved service < target

    **Policy Configs Table:**
    - **DCC (%)** = Demand-Curve Coverage (service level) per segment
    - **Safety Stock (%)** = Buffer inventory as % of POG capacity
    - **MOQ Threshold** = Minimum order quantity (computed as 5% of segment demand)
    - **End of Season %** = Reserve for end-of-season markdowns
    """)

st.markdown("---")

st.subheader("Scenario Explorer")
st.caption("Type a natural language scenario to see instant policy changes with trade-off narration.")
st.caption("**Supported:** Budget changes ($XM or X%), service target changes (X%), lead time or demand changes. Non-sensical inputs will be rejected.")

scenario_input = st.text_input(
    "What-if Scenario",
    placeholder="e.g., What if budget drops $3M? What if lead time doubles for vendor X?",
    key="scenario_input"
)

run_scenario = st.button("Run Scenario", width='stretch')

if run_scenario and scenario_input:
    if not st.session_state.current_policy:
        st.warning("Please run Optimize first to get a baseline policy.")
    else:
        with st.spinner("Running scenario..."):
            st.session_state.scenario_result = cal_scenario(
                nl_input=scenario_input,
                current_policy=st.session_state.current_policy,
                budget=budget,
                target=service_target,
                dept_id=selected_dept_id,
                dept_ids=selected_dept_ids
            )

# Display scenario result (outside button block)
scenario_result = st.session_state.get("scenario_result")
if scenario_result:
    if scenario_result.get("error"):
        # Validation error or invalid input
        guidance = scenario_result.get("guidance", "Supported: budget changes ($XM or X%), service target changes (X%), lead time or demand changes.")
        st.error(f"**Invalid Scenario:** {guidance}")
    else:
        narration = scenario_result.get("narration", "")
        if narration:
            st.success("**Scenario Results:**")
            st.write(narration)
            if scenario_result.get("configs"):
                st.session_state.current_policy = scenario_result["configs"]
        else:
            st.error(f"Scenario failed. Result: {scenario_result}")

# --- Decision Center ---

st.markdown("---")
st.subheader("High-Stakes Decision Center")
st.caption("AI-powered decision framing with quantified trade-offs for mid-season decisions.")
st.caption("**Supported:** Demand changes (under/overforecast), supply chain issues (vendor delay, transport cost), inventory problems, cost changes. Non-sensical inputs will be rejected.")

decision_context = st.text_area(
    "Decision Context",
    placeholder="e.g., Underforecasted holiday by 20% for Product X, 1 week left. Do we place POs?",
    key="decision_context"
)

if st.button("Frame Decision", width='stretch') and decision_context:
    with st.spinner("Framing decision..."):
        current_service = result.get("achieved_service", service_target) if result else service_target
        decision_result = cal_decision(
            context=decision_context,
            dept_id=selected_dept_id,
            dept_ids=selected_dept_ids,
            budget=budget,
            service=current_service
        )

        if decision_result.get("error"):
            # Validation error or invalid input
            guidance = decision_result.get("guidance", "Describe a mid-season issue: demand change, supply delay, inventory problem, or cost increase.")
            st.error(f"**Invalid Decision Context:** {guidance}")
        else:
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
                        up_m = upside / 1_000_000
                        down_m = abs(downside or 0) / 1_000_000
                        st.text(f"Upside: ${up_m:.1f}M  |  Downside: -${down_m:.1f}M")
                    # Show explanation if available (explains what upside/downside mean)
                    explanation = opt.get("explanation")
                    if explanation:
                        st.markdown(f"ℹ️ {explanation}")
                    else:
                        st.markdown("ℹ️ **Upside/Downside** = net financial impact in dollars (gain if positive, loss if negative).")
                with col2:
                    if st.button("Select", key=f"select_{opt.get('option', '')}"):
                        st.session_state.selected_decision = opt.get('option')

            st.info(f"**Recommendation:** {decision_result.get('recommendation', '')}")

        if st.session_state.selected_decision:
            st.success(f"Selected: {st.session_state.selected_decision}")

# --- Footer ---

st.markdown("---")
st.caption(
    "Foxtrot V0 — AI-Powered Inventory Policy Optimizer  |  "
    "Built for CBOs who want to explore 20+ scenarios in the time it takes to do 2 in Excel."
)
