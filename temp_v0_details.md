╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
 Plan: Foxtrot V0 Product Architecture

 Context

 Foxtrot (PlanPilot) is an AI-powered inventory policy optimization tool for
 retail Category Business Owners (CBOs). The repository contains validated
 documentation but no code. V0 must be demo-able to a startup panel in 2 working
 days, deployable to Streamlit Cloud for panel experimentation.

 Core problem: Inventory policies that control automated replenishment are
 defined in Excel with no optimization. Teams explore 2-3 scenarios when 20+
 should be evaluated.

 V0 goal: Functional prototype with unconstrained optimizer + LLM-powered
 trade-off narration for single department, with data layer supporting 50
 departments and category mapping (e.g., Category: "Apparel & Accessories" → Dept
  456 "Shoes"). Multi-department optimization as stretch goal.

 Key behavior: CBO inputs budget + target → optimizer computes minimum budget
 needed. If insufficient: "You need $115M for 97% WIP. Options: (1) Increase to
 $115M, (2) Keep $100M → 94% WIP, (3) Lower target to 94%."

 Hosting: Streamlit Cloud (free, deploy from GitHub, public URL, multi-session
 support for panel members to experiment).

 ---
 V0 Architecture

 System Components

 ┌─────────────────────────────────────────────────────────┐
 │                    CBO User (Primary)                    │
 │         Budget + service target input, scenario input     │
 │         trade-off visualization, decision approval        │
 └────────────────────────┬────────────────────────────────┘
                          │
                          ▼
 ┌─────────────────────────────────────────────────────────┐
 │              Frontend (Streamlit + Streamlit Cloud)       │
 │  • Category → Department selector (50 depts, 5-10 cats)│
 │  • Budget + service-level target input (per dept)         │
 │  • Budget feasibility alert (if target unachievable)     │
 │  • Policy config output (DCC, safety stock per segment)  │
 │  • Natural language scenario input + LLM narration        │
 │  • Multi-dept stretch: total budget across 50 depts      │
 │  • Basic config auto-execute toggle                      │
 │  • High-stakes decision surfacing                       │
 └────────────────────────┬────────────────────────────────┘
                          │ HTTP
                          ▼
 ┌─────────────────────────────────────────────────────────┐
 │              Backend API (Python FastAPI)                │
 │                                                          │
 │  ┌─────────────────┐  ┌─────────────────────────────┐  │
 │  │ Optimization     │  │ LLM Layer (Anthropic Claude)│  │
 │  │ Engine           │  │                             │  │
 │  │ (OR-Tools)      │  │ • Intent → Parameters       │  │
 │  │                  │  │ • Trade-off narration       │  │
 │  │ UNCONSTRAINED:  │  │ • Decision framing         │  │
 │  │ Computes optimal │  │ • Constraint synthesis     │  │
 │  │ configs for     │  │ • Explain infeasibility    │  │
 │  │ target OR budget │  └─────────────────────────────┘  │
 │  │                  │                                     │
 │  │ Single dept +    │  ┌─────────────────────────────┐  │
 │  │ (stretch) multi │  │ Data Layer (JSON files)     │  │
 │  │ dept allocation  │  │ • 50 departments           │  │
 │  └─────────────────┘  │ • Categories (5-10)         │  │
 │        │               │ • Demand forecasts          │  │
 │        ▼               │ • Vendor inputs             │  │
 │  ┌─────────────────┐  │ • Item segments (A/B/C/R)   │  │
 │  │ Policy Config    │  │ • Historical policy perf     │  │
 │  │ Store            │  └─────────────────────────────┘  │
 │  └─────────────────┘                                     │
 └────────────────────────────────────────────────────────────┘

 Component Details

 1. Frontend — Streamlit + Streamlit Cloud

 - Why Streamlit: Rapid prototyping, Python-native, demo-ready in hours.
 - Hosting: Streamlit Community Cloud — deploy from GitHub repo, get public URL
 (e.g., foxtrot-demo.streamlit.app). Panel members open URL, each gets own
 session.
 - Screens:
   - Category/Department selector: Dropdown 1: Category (e.g., "Apparel &
 Accessories"), Dropdown 2: Department (e.g., "Dept 456 - Shoes"). Data supports
 50 depts across 5-10 categories.
   - Input: Budget ($), service level target (%), season.
   - Output: Policy configs per segment (A/B/C/R) with DCC %, safety stock %,
 allocation splits.
   - Budget feasibility alert (key feature):
   ⚠️  Budget Insufficient
 Target: 97% WIP with $100M is not achievable.
 Minimum budget required: $115M.

 Your options:
 1. Increase budget to $115M → achieve 97% WIP
 2. Keep $100M → achieve 94.2% WIP (see configs)
 3. Lower target to 94% → achieve with $100M
   - Scenario explorer: NL input → updated configs + LLM narration.
   - Multi-dept stretch (Day2 PM if ahead): Total budget input ($1.5B across 50
 depts) → optimal allocation per dept.
   - Decision center: High-stakes decisions with quantified trade-offs.

 2. Backend API — FastAPI

 - Endpoints:
   - POST /optimize — Budget + target + dept_id → policy OR feasibility warning.
   - POST /scenario — NL what-if + current policy → updated configs + LLM
 narration.
   - POST /decision — High-stakes decision context → trade-off analysis.
   - POST /optimize/multi (stretch) — Total budget + 50 depts → optimal
 allocation per dept.
   - GET /departments — List all 50 departments with categories.
 - Response structure:
 {
   "feasible": true|false,
   "minimum_budget": null|$115M,
   "achieved_service": 97%|94.2%,
   "configs": { "A": {"dcc": 98%, "safety_stock": 25%}, ... },
   "options": ["increase_budget", "lower_target", "show_whats_possible"]
 }

 3. Optimization Engine — OR-Tools (Python)

 - Data: 50 departments organized under 5-10 categories (e.g., "Apparel &
 Accessories" → Depts 450-460).
 - Unconstrained approach:
   a. Compute min budget for target: Given service target (97%), find cheapest
 configs. If cost > budget → return infeasibility + min_budget.
   b. Compute max service for budget: Given budget ($100M), maximize service
 level within budget.
   c. Bidirectional: Target → min budget, and budget → max service.
 - Model:
   - Variables: DCC per segment (0-100%), safety stock factor per segment,
 allocation % (pre/in/post season).
   - Relationships: Safety stock = z-score × √(lead time) × demand σ. Segment
 priority: R > A > B > C.
   - Objective (Mode 1): Minimize total cost subject to service_level ≥ target.
   - Objective (Mode 2): Maximize weighted service level subject to total_cost ≤
 budget.
   - Cost model: Inventory holding cost + stockout penalty (demand lost ×
 margin).
 - Output includes:
   - DCC % per segment (A=98%, B=95%, C=90%, R=99%)
   - Safety stock % of POG per segment
   - Reorder points, order frequency, MOQ thresholds
   - Pre-season / in-season / markdown allocation splits (fashion=60/30/10,
 basics=20/70/10)
   - Total cost, achieved service level, inventory turns
 - Stretch (multi-dept): Allocate total budget across 50 depts to maximize total
 weighted service. Per-dept optimizer runs in a loop; gradient-based adjustment
 for cross-dept allocation.

 4. LLM Layer — Anthropic Claude API

 - Intent → Parameters: Parse "budget drops $3M" into optimizer parameter
 changes.
 - Trade-off narration: "Reducing DCC on C-items from 90% to 85% saves $2.1M but
 increases stockout risk 2.4%. Last cycle, similar settings caused 4 stockout
 incidents."
 - Decision framing: For high-stakes decisions, present ranked options with
 upside/downside.
 - Constraint synthesis: "Cut $3M" → generate and rank multiple strategies.
 - Budget feasibility narrative: Explain WHY $100M can't achieve 97% WIP in
 business language.
 - Why Claude: Highest reasoning capability, function calling for structured
 outputs, large context window.

 5. Data Layer — JSON files (50 departments, 5-10 categories)

 - Structure:
 backend/data/
 ├── categories.json          # 5-10 categories (e.g., "Apparel & Accessories")
 ├── departments.json        # 50 depts mapped to categories (e.g., dept 456
 "Shoes" → cat_id 5)
 ├── demand/
 │   ├── dept_456.json      # Demand forecast for dept 456 (10-20 SKU clusters,
 A/B/C/R)
 │   ├── dept_789.json
 │   └── ... (50 depts)
 ├── vendors.json            # Vendor inputs: lead times, MOQs, cost curves
 └── segments.json          # Segment definitions (A/B/C/R) with default DCC %,
 safety stock %
 - Category mapping example:
 {
   "categories": [
     {"id": 1, "name": "Apparel & Accessories"},
     {"id": 2, "name": "Home Essentials"}
   ],
   "departments": [
     {"id": 456, "name": "Shoes", "category_id": 1},
     {"id": 457, "name": "Outerwear", "category_id": 1},
     {"id": 123, "name": "Home Storage", "category_id": 2}
   ]
 }

 ---
 V0 Scope

 ┌────────────────────────────┬───────────┬──────────────────────────────────┐
 │          Feature           │ Included? │              Notes               │
 ├────────────────────────────┼───────────┼──────────────────────────────────┤
 │ 50 departments with        │ ✅        │ Data layer supports all 50,      │
 │ category mapping           │           │ frontend dropdown                │
 ├────────────────────────────┼───────────┼──────────────────────────────────┤
 │ Category → Dept selector   │ ✅        │ Two-level dropdown: Category →   │
 │ (frontend)                 │           │ Department                       │
 ├────────────────────────────┼───────────┼──────────────────────────────────┤
 │ Single dept: budget +      │ ✅        │ Core input (e.g., Dept 456       │
 │ service target input       │           │ "Shoes")                         │
 ├────────────────────────────┼───────────┼──────────────────────────────────┤
 │ Unconstrained optimizer    │ ✅        │ Key: rejects insufficient budget │
 │ (budget ↔ target)          │           │  with min needed                 │
 ├────────────────────────────┼───────────┼──────────────────────────────────┤
 │ LLM intent parsing for     │ ✅        │ NL → param changes               │
 │ scenarios                  │           │                                  │
 ├────────────────────────────┼───────────┼──────────────────────────────────┤
 │ LLM trade-off narration    │ ✅        │ Business-language output         │
 ├────────────────────────────┼───────────┼──────────────────────────────────┤
 │ Budget feasibility alert + │ ✅        │ Increase budget / lower target / │
 │  3 options                 │           │  show what's possible            │
 ├────────────────────────────┼───────────┼──────────────────────────────────┤
 │ Scenario exploration       │ ✅        │ Core value demo                  │
 │ (instant)                  │           │                                  │
 ├────────────────────────────┼───────────┼──────────────────────────────────┤
 │ Two-tier execution: basic  │ ✅        │ Simulated (log to console)       │
 │ configs auto-execute       │           │                                  │
 ├────────────────────────────┼───────────┼──────────────────────────────────┤
 │ High-stakes decision       │ ✅        │ Display trade-offs, approval     │
 │ surfacing                  │           │ button                           │
 ├────────────────────────────┼───────────┼──────────────────────────────────┤
 │ Streamlit Cloud hosting    │ ✅        │ Public URL for panel             │
 │                            │           │ experimentation                  │
 ├────────────────────────────┼───────────┼──────────────────────────────────┤
 │ Stretch: Multi-dept (50    │ 🟡        │ If time permits Day2 PM          │
 │ depts)                     │           │                                  │
 ├────────────────────────────┼───────────┼──────────────────────────────────┤
 │ Integration with internal  │ ❌        │ V1                               │
 │ simulation                 │           │                                  │
 ├────────────────────────────┼───────────┼──────────────────────────────────┤
 │ Integration with           │ ❌        │ V1                               │
 │ replenishment systems      │           │                                  │
 ├────────────────────────────┼───────────┼──────────────────────────────────┤
 │ Multi-user auth (beyond    │ ❌        │ V1 (Streamlit Cloud handles      │
 │ Streamlit sessions)        │           │ sessions)                        │
 ├────────────────────────────┼───────────┼──────────────────────────────────┤
 │ Dynamic segmentation       │ ❌        │ V1 (static segments for V0)      │
 └────────────────────────────┴───────────┴──────────────────────────────────┘

 ---
 2-Day Implementation Timeline

 Day 1: Core Engine + API + Data

 Morning (4h):
 - Project setup: directory structure, venv, install dependencies
 - Create data layer: categories.json, departments.json (50 depts, 5-10 cats)
 - Create demand/dept_456.json (Shoes) + 2-3 more depts for testing
 - Create vendors.json, segments.json
 - Implement models.py — Pydantic request/response models
 - Implement GET /departments endpoint (list all depts with categories)

 Afternoon (4h):
 - Implement optimizer.py — OR-Tools unconstrained optimizer
   - compute_min_budget(target) → minimum budget for target
   - optimize_policy(budget, target, dept_id) → policy configs OR infeasibility
   - Model: safety stock = f(z-score, √lead_time, demand_σ), segment priorities
 - Test optimizer: $100M/97% → expect infeasibility with $115M min
 - Implement main.py — FastAPI with POST /optimize endpoint
 - Test API: POST /optimize with $100M/97% → feasibility warning

 Day 2: LLM + Frontend + Integration + Streamlit Cloud Deploy

 Morning (4h):
 - Implement llm_layer.py — Anthropic Claude integration
   - parse_scenario(), narrate_tradeoff(), explain_infeasibility()
 - Add POST /scenario and POST /decision endpoints to main.py
 - Test: POST /optimize with $115M → policy with 97% WIP
 - Test: POST /scenario with "cut $3M" → updated configs + narration

 Afternoon (4h):
 - Implement app.py — Streamlit frontend
   - Category → Department two-level dropdown (50 depts)
   - Budget + service target input, "Optimize" button
   - Feasibility alert with 3 options (increase budget / lower target / show)
   - Policy display: DCC %, safety stock %, allocation splits per segment
   - Scenario input + LLM narration display
   - Decision center section
 - Integration test: end-to-end demo flow
 - Deploy to Streamlit Cloud: Push to GitHub → connect repo → get public URL
 - Stretch (if ahead): Multi-dept support
   - Add POST /optimize/multi endpoint (50 depts, total budget allocation)
   - Update frontend: total budget input, department-wise results table
 - Demo prep: 3-minute script (pain point → V0 solution → feasibility handling →
 LLM narration)

 ---
 Implementation Steps

 Step 1: Project setup (Day 1 Morning)

 Foxtrot/
 ├── backend/
 │   ├── main.py          # FastAPI app
 │   ├── optimizer.py     # OR-Tools unconstrained optimization
 │   ├── llm_layer.py    # Anthropic Claude integration
 │   ├── models.py       # Pydantic request/response models
 │   ├── data/
 │   │   ├── categories.json      # 5-10 categories
 │   │   ├── departments.json     # 50 depts mapped to categories
 │   │   ├── demand/             # Per-department demand forecasts
 │   │   │   ├── dept_456.json
 │   │   │   └── ... (50 depts)
 │   │   ├── vendors.json
 │   │   └── segments.json
 │   └── requirements.txt
 ├── frontend/
 │   ├── app.py          # Streamlit app
 │   └── requirements.txt
 ├── .streamlit/
 │   └── config.toml    # Streamlit Cloud config
 ├── CLAUDE.md
 ├── plan.md
 ├── .env                # ANTHROPIC_API_KEY (gitignored)
 └── .gitignore
 - pip install fastapi uvicorn ortools anthropic pydantic streamlit python-dotenv
  requests

 Step 2: Data layer (Day 1 Morning)

 - backend/data/categories.json: 5-10 categories (e.g., "Apparel & Accessories",
 "Home Essentials", "Electronics", etc.)
 - backend/data/departments.json: 50 departments mapped to categories (e.g., dept
  456 "Shoes" → category "Apparel & Accessories")
 - backend/data/demand/dept_456.json: Demand forecast for Shoes (10-20 SKU
 clusters, A/B/C/R segments, demand mean/σ per segment)
 - backend/data/vendors.json: Lead times, MOQs, cost curves for sample vendors
 - backend/data/segments.json: Segment definitions (A=high velocity, B=mid,
 C=low, R=reliability) with default DCC % and safety stock %

 Step 3: Optimization engine (Day 1 Afternoon)

 - backend/optimizer.py:
   - compute_min_budget(service_target, dept_id) → {min_budget: $115M, configs:
 {...}}
   - optimize_policy(budget, service_target, dept_id) → {feasible, min_budget,
 configs, achieved_service}
   - Uses OR-Tools for linear/integer programming
   - Key formulas:
       - safety_stock = z_score(service_level) * sqrt(lead_time) * demand_std_dev
     - total_cost = sum(safety_stock * holding_cost) + stockout_penalty
     - Segment priority: R-items get highest DCC (99%), then A (98%), B (95%), C
 (90%)
   - Output: DCC per segment, safety stock %, reorder points, MOQ thresholds,
 allocation splits

 Step 4: Backend API (Day 1 Afternoon)

 - backend/main.py:
   - GET /departments → list all 50 depts with categories (for frontend dropdown)
   - POST /optimize: Calls optimizer → returns policy OR {feasible: false,
 min_budget: $115M, options: [...]}
   - POST /scenario: LLM parses NL → optimizer recomputes → LLM narrates
 trade-offs
   - POST /decision: LLM frames high-stakes decision with options
   - CORS middleware for Streamlit frontend
   - Error handling, logging

 Step 5: LLM layer (Day 2 Morning)

 - backend/llm_layer.py:
   - parse_scenario(nl_input, current_policy) → {"action": "reduce_budget",
 "value": 3000000, ...}
   - narrate_tradeoff(old_policy, new_policy) → "Reducing DCC on C-items saves
 $2.1M but..."
   - explain_infeasibility(budget, target, min_budget) → "Your $100M cannot
 achieve 97% WIP because..."
   - frame_decision(decision_context) → ranked options with upside/downside
   - Use Claude Sonnet via Anthropic API with function calling for structured
 outputs

 Step 6: Frontend + Streamlit Cloud (Day 2 Afternoon)

 - frontend/app.py:
   - Category/Dept selector: Two st.selectbox — Category → filters Department
 dropdown (50 depts total)
   - Sidebar: Budget input, service target slider, season dropdown
   - "Optimize" button: Calls GET /departments → POST /optimize
   - Feasibility alert: If feasible=false, display 3 options with st.button for
 each:
       - "Increase Budget to $X" → updates input, re-optimize
     - "Keep $Y → Show Z% WIP" → show policy for reduced target
     - "Lower Target to Z%" → update target, re-optimize
   - Policy display: st.metric, st.bar_chart for DCC %, safety stock %,
 allocation splits per segment
   - Scenario input: st.text_input + "Run Scenario" button → calls /scenario →
 displays updated configs + LLM narration
   - Decision center: Hardcoded high-stakes examples with trade-off display
 - Streamlit Cloud deployment:
   - Push to GitHub repo
   - Sign in to streamlit.io/cloud with GitHub
   - Deploy from repo → get public URL (e.g., foxtrot-demo.streamlit.app)
   - Panel members open URL → each gets own session → experiment with scenarios

 Step 7: Integration & Stretch Goal (Day 2 Afternoon)

 - Start backend locally: uvicorn main:app --reload (for local testing before
 deploy)
 - Test end-to-end: Category → Dept 456 → $100M/97% → feasibility warning → $115M
  → policy → scenario "cut $3M" → narration
 - Deploy: Push to GitHub → Streamlit Cloud auto-deploys → test public URL
 - Stretch: Add POST /optimize/multi for 50 departments:
   - Input: {"total_budget": 1.5e9, "departments": [{"id": "dept_456", "target":
 97}, ...]}
   - Logic: Allocate budget across 50 depts to maximize total weighted service
 (gradient adjustment)
   - Update frontend: total budget input, department-wise results table with
 allocations

 ---
 Key Files to Create

 ┌───────────────────────────────────┬────────────────────────────────────────┐
 │               File                │                Purpose                 │
 ├───────────────────────────────────┼────────────────────────────────────────┤
 │ backend/main.py                   │ FastAPI app with endpoints             │
 ├───────────────────────────────────┼────────────────────────────────────────┤
 │ backend/optimizer.py              │ OR-Tools unconstrained optimization    │
 │                                   │ engine                                 │
 ├───────────────────────────────────┼────────────────────────────────────────┤
 │ backend/llm_layer.py              │ Anthropic Claude LLM integration       │
 ├───────────────────────────────────┼────────────────────────────────────────┤
 │ backend/models.py                 │ Pydantic models for requests/responses │
 ├───────────────────────────────────┼────────────────────────────────────────┤
 │ backend/data/categories.json      │ 5-10 categories                        │
 ├───────────────────────────────────┼────────────────────────────────────────┤
 │ backend/data/departments.json     │ 50 departments mapped to categories    │
 ├───────────────────────────────────┼────────────────────────────────────────┤
 │ backend/data/demand/dept_456.json │ Demand forecast for dept 456 (Shoes)   │
 ├───────────────────────────────────┼────────────────────────────────────────┤
 │ backend/data/vendors.json         │ Mock vendor inputs                     │
 ├───────────────────────────────────┼────────────────────────────────────────┤
 │ backend/data/segments.json        │ Item segment definitions               │
 ├───────────────────────────────────┼────────────────────────────────────────┤
 │ frontend/app.py                   │ Streamlit frontend with category/dept  │
 │                                   │ selector                               │
 ├───────────────────────────────────┼────────────────────────────────────────┤
 │ .streamlit/config.toml            │ Streamlit Cloud configuration          │
 ├───────────────────────────────────┼────────────────────────────────────────┤
 │ .env                              │ Environment variables                  │
 │                                   │ (ANTHROPIC_API_KEY)                    │
 ├───────────────────────────────────┼────────────────────────────────────────┤
 │ .gitignore                        │ Exclude .env, pycache, etc.            │
 └───────────────────────────────────┴────────────────────────────────────────┘

 ---
 Verification

 1. Optimizer unit tests (Day 1 EOD):

 - compute_min_budget(97%) → returns $115M (example)
 - optimize_policy($100M, 97%) → {feasible: false, min_budget: $115M}
 - optimize_policy($115M, 97%) → {feasible: true, achieved_service: 97%}
 - optimize_policy($100M, 94%) → {feasible: true, achieved_service: 94%}
 - Test scenario: reduce budget → DCC/safety stock decrease

 2. API integration tests (Day 2 Morning):

 - GET /departments → returns 50 depts with categories
 - POST /optimize with $100M/97% → feasibility warning with $115M minimum
 - POST /optimize with $115M/97% → policy achieving 97% WIP
 - POST /scenario with "cut $3M" → updated configs + LLM narration
 - Verify LLM integration works (need Anthropic API key)

 3. End-to-end test (Day 2 Afternoon):

 - Open Streamlit app (local or deployed)
 - Select: Category "Apparel & Accessories" → Dept 456 "Shoes"
 - Input: Budget $100M, service target 97%
 - Expect: Feasibility warning "Need $115M" + 3 options displayed
 - Select: "Increase Budget to $115M" → Expect: Policy configs with 97% WIP
 - Input scenario: "What if budget drops to $95M?"
 - Expect: Updated configs + LLM narration explaining trade-offs
 - Verify Streamlit Cloud deployment: panel members can open URL and experiment

 4. Stretch (if implemented):

 - Test POST /optimize/multi with 50 depts → verify budget allocation + per-dept
 policies
 - Update frontend: total budget input → department-wise results table

 5. Demo readiness check:

 - 3-minute demo script prepared:
   a. Show pain point (Excel, 2-3 scenarios, $11-31M lost)
   b. Show V0 solution (instant scenario exploration, 20+ scenarios)
   c. Key differentiator: Budget infeasibility handling ("Need $115M" + 3
 options)
   d. LLM trade-off narration (business-language explanations)
   e. Streamlit Cloud URL for panel to experiment
 - App runs end-to-end on Streamlit Cloud without errors
 - Key features work: optimizer, LLM narration, feasibility alert

    
     2. API integration tests (Day 2 Morning):

     - GET /departments → returns 50 depts with categories                    
     - POST /optimize with $100M/97% → feasibility warning with $115M minimum 
     - POST /optimize with $115M/97% → policy achieving 97% WIP               
     - POST /scenario with "cut $3M" → updated configs + LLM narration        
     - Verify LLM integration works (need Anthropic API key)                  
                                                                              
     3. End-to-end test (Day 2 Afternoon):                                    
                                                                              
     - Open Streamlit app (local or deployed)                                 
     - Select: Category "Apparel & Accessories" → Dept 456 "Shoes"            
     - Input: Budget $100M, service target 97%                                
     - Expect: Feasibility warning "Need $115M" + 3 options displayed         
     - Select: "Increase Budget to $115M" → Expect: Policy configs with 97% WIP
     - Input scenario: "What if budget drops to $95M?"                        
     - Expect: Updated configs + LLM narration explaining trade-offs          
     - Verify Streamlit Cloud deployment: panel members can open URL and      
     experiment                                                               
                                                                              
     4. Stretch (if implemented):                                             
                                                                              
     - Test POST /optimize/multi with 50 depts → verify budget allocation +   
     per-dept policies                                                        
     - Update frontend: total budget input → department-wise results table    
                                                                              
     5. Demo readiness check:                                                 
                                                                              
     - 3-minute demo script prepared:                                         
       a. Show pain point (Excel, 2-3 scenarios, $11-31M lost)
       b. Show V0 solution (instant scenario exploration, 20+ scenarios)
       c. Key differentiator: Budget infeasibility handling ("Need $115M" + 3
     options)
       d. LLM trade-off narration (business-language explanations)          
       e. Streamlit Cloud URL for panel to experiment
     - App runs end-to-end on Streamlit Cloud without errors          
     - Key features work: optimizer, LLM narration, feasibility alert          
                         
     ---                                                                    
     Risks & Mitigations
                                                                           
     ┌────────────────────────┬──────────────────────────────────────────────────┐
     │          Risk          │                    Mitigation                    │
     ├────────────────────────┼──────────────────────────────────────────────────┤
     │ 2-day timeline too     │ Focus on single dept optimization; multi-dept is │
     │ tight                  │  stretch. Skip over-engineering.                 │
     ├────────────────────────┼──────────────────────────────────────────────────┤
     │ LLM API latency        │ Cache optimization results; LLM narration can be │
     │                        │  async if needed.                                │
     ├────────────────────────┼──────────────────────────────────────────────────┤
     │ OR-Tools learning      │ Start with simple linear model; iterate          │
     │ curve                  │ complexity in V1.                                │
     ├────────────────────────┼──────────────────────────────────────────────────┤
     │ Anthropic API cost     │ Use Claude Sonnet (cheaper); limit calls during  │
     │                        │ testing.                                         │
     ├────────────────────────┼──────────────────────────────────────────────────┤
     │ Mock data unrealistic  │ Use synthetic data based on problem document     │
     │                        │ examples (A/B/C/R, $100M, 97% WIP).              │
     ├────────────────────────┼──────────────────────────────────────────────────┤
     │ LLM unavailable during │ Build fallback: display trade-offs as structured │
     │  demo                  │  text if API fails.                              │
     ├────────────────────────┼──────────────────────────────────────────────────┤
     │ Streamlit Cloud deploy │ Test deploy on Day 2 morning (not last minute).  │
     │  issues                │ Keep local demo as backup.                       │
     ├────────────────────────┼──────────────────────────────────────────────────┤
     │ 50 depts data too much │ Generate programmatically with Python script.    │
     │  for 2 days            │ Use same demand template per dept.               │
     └────────────────────────┴──────────────────────────────────────────────────┘

     ---
     Success Criteria for V0

     - Data layer: 50 departments mapped to 5-10 categories, accessible via GET
     /departments
     - Frontend: Category → Department two-level selector works (50 depts)
     - CBO inputs budget + service target → optimizer returns policy OR
     feasibility warning within 5 seconds
     - If budget insufficient → CBO sees: "Need $X to hit target" + 3 actionable
     options
     - CBO can type NL scenario ("cut $3M") and see updated configs + trade-off
     narration within 10 seconds
     - Basic configs can be "auto-executed" (simulated log to console)
     - High-stakes decision example displayed with quantified trade-offs
     - Deployed to Streamlit Cloud: Public URL works, panel members can experiment
     - Stretch: Multi-dept (50 depts) budget allocation works
     - Demo-ready in 2 working days