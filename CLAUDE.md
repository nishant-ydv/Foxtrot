# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Foxtrot (PlanPilot)** — an AI-powered inventory policy optimization tool for retail Category Business Owners (CBOs). The product translates budget + service-level goals into optimal inventory configs (safety stock, DCC/service levels, reorder points, MOQ thresholds) across item segments, enabling instant scenario exploration that currently takes hours in Excel.

**Stage:** V0 — Core optimizer and Streamlit frontend working. Deployable to Streamlit Cloud.

## Development Commands

# Backend
cd backend && source venv/bin/activate
python -m uvicorn main:app --host 0.0.0.0 --port 8000  # Start FastAPI server

# Frontend (local)
cd frontend && source venv/bin/activate
streamlit run app.py --server.port 8501

# Test optimizer directly (standalone, no server needed)
python3 -c "import sys; sys.path.insert(0, 'backend'); from optimizer import optimize_policy; print(optimize_policy(100000000, 97.0, 101, 'Fall/Holiday'))"

# Test API endpoints
curl -s http://localhost:8000/health
curl -s -X POST http://localhost:8000/optimize -H "Content-Type: application/json" -d '{"budget": 100000000, "service_target": 97, "dept_id": 101, "season": "Fall/Holiday"}'

## Code Architecture

```
Foxtrot/
├── backend/
│   ├── main.py           # FastAPI app — /optimize, /scenario, /decision endpoints
│   ├── optimizer.py      # OR-Tools unconstrained optimizer
│   ├── llm_layer.py      # Anthropic Claude integration (scenario parsing, narration, decisions)
│   ├── models.py         # Pydantic request/response models
│   ├── generate_demand.py # Demand data generator
│   ├── data/
│   │   ├── demand/       # Per-department demand forecasts (dept_101.json, etc.)
│   │   ├── categories.json
│   │   ├── departments.json
│   │   ├── segments.json
│   │   └── vendors.json
│   └── venv/
├── frontend/
│   ├── app.py           # Streamlit app — CBO-facing UI
│   ├── requirements.txt   # Includes ortools, anthropic, pydantic (standalone mode)
│   └── venv/
└── .env                  # Gitignored — API keys (ANTHROPIC_API_KEY, etc.)
```

### Key Design Decisions

- **Standalone mode:** `frontend/app.py` imports `backend/optimizer.py` and `backend/llm_layer.py` directly. No separate backend server needed for Streamlit Cloud deployment.
- **Unconstrained optimizer:** If budget < minimum required → returns infeasibility + 3 options (increase budget, lower target, show what's possible).
- **LLM reads from env vars:** `llm_layer.py` uses `os.getenv("ANTHROPIC_API_KEY")` — no keys in code. Supports `ANTHROPIC_MODEL` override (default: `tencent/hy3-preview:free`).
- **Streamlit Cloud:** Deploy with main file `frontend/app.py`, requirements `frontend/requirements.txt`.

## Key Documents

| Document | Purpose |
|---|---|
| `Executive Problem Statement.md` | Concise problem statement for leadership/investors |
| `Problem Reframe & Workflow Map.md` | Validated user workflow (12-step), pain points ranked #1-#7, V1-V8 validation answers, $11-31M preventable loss analysis |
| `AI Layer Defense.md` | Three-layer architecture: Optimization Engine (math/OR), Scenario Simulation (ML), LLM Layer (intent→params, trade-off narration, decision framing) |
| `Competitive Landscape.md` | Tier 1-3 competitive analysis |
| `Inventory Policy Idea.md` | Original idea brief |
| `Retail Product Ideas.md` | Four idea contenders — Foxtrot (Idea 1) was selected |

## Core Problem

At large retailers, inventory policies (safety stock, DCC, reorder points) that control automated replenishment for 3-4 months are defined entirely in Excel. Each "what if" scenario takes hours, so teams explore 2-3 scenarios when 20+ should be evaluated. On a $100M budget, suboptimal policies cost $11-31M per cycle in avoidable markdowns and lost sales.

**Internal data science teams have simulations** that show what configs *do* downstream — but no tool answers the upstream question: **given my budget and goals, what should the configs *be*?**

## Product Architecture

- **Upstream of** existing simulation and replenishment systems (Blue Yonder, Oracle Retail)
- **Primary user:** Category Business Owner (CBO) — owns P&L, makes strategic decisions
- **Secondary user:** Inventory Planner — hands-on spreadsheet work (later phase)
- **Two-tier execution:** Auto-execute routine configs (DCC values, safety stock percentages); surface high-stakes decisions (mid-season chase/abandon calls) with quantified trade-offs for human approval
- **LLM value layer:** Translates business intent → optimization parameters, narrates trade-offs, frames decisions, synthesizes constraint options

## Key Concepts

| Term | Meaning |
|---|---|
| **CBO** | Category Business Owner — primary user, owns P&L for a department |
| **DCC** | Demand-Curve Coverage — identical to service level / in-stock % |
| **WIP** | Walk-In Purchasability — the customer experience of finding items in stock |
| **A/B/C/R segments** | Item tiers by velocity/margin: A=high, B=mid, C=low, R=reliability (must always be in stock). 10-20% of items shift segments quarterly |
| **OTB** | Open-to-Buy: `Planned Sales + Markdowns + End Inventory - Beginning Inventory - On-Order` |
| **Pre-season vs In-season** | Pre-season: 20-60% of budget committed via manual POs (irreversible). In-season: remaining 40-80% controlled by automated replenishment engine using the policies we configure |
| **Basic configs** | Routine outputs like "DCC=97% for SKU1", "Safety stock=30% of POG" — auto-executable |
| **High-stakes decisions** | Mid-season calls requiring human judgment — e.g., "underforecasted by 20%, do we chase?" or "transport cost doubled, do we still chase the goal?" |

## Seasonal Workflow (Validated)

1. **Trigger** — Seasonal planning cycle begins (pre-season/quarterly)
2. **Goal Setting** — CBO sets budget + service level target
3. **Demand Intake** — Planner receives forecast from Demand team
4. **Vendor Input** — Lead times, MOQs, cost curves collected
5. **First-Pass Plan** 🔴 — Planner builds policy in Excel (12-20 tab workbooks)
6. **Budget Reconciliation** — Submit to Finance for approval
7. **Approval** — If rejected, iterate back to Step 5
8. **Plan Finalization** — Lock DCC, safety stock, allocation splits
9. **System Configuration** — Push params into replenishment systems
10. **Execution** — Automated purchasing/replenishment
11. **Mid-Season Review** — Re-plan if reality diverges (rarely done due to cost)

**Bottleneck breakdown:** 50% keyboard work (Excel), 30% coordination, 20% approvals. Operations/DC validation is **out of scope**.

## Competitive Moat

No incumbent or startup offers natural language scenario exploration at the CBO's "budget → policy" altitude. RELEX is the closest threat (12-18 month horizon). Foxtrot wins on: CBO-centric UX (not planner-centric), LLM-powered intent translation, instant what-if at strategy level, and days-to-pilot vs. 12-18 month enterprise implementations.
