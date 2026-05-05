# Foxtrot (PlanPilot)

<p align="center">
  <a href="https://foxtrotpilot.streamlit.app/">
    <img src="https://img.shields.io/badge/🌐%20Live%20App-foxtrotpilot.streamlit.app-2ea32a?style=for-the-badge" alt="Live App">
  </a>
  <a href="https://github.com/nishant-ydv/foxtrot">
    <img src="https://img.shields.io/badge/GitHub-nishant--ydv%2Ffoxtrot-181717?style=for-the-badge&logo=github" alt="GitHub">
  </a>
  <a href="https://raw.githubusercontent.com/nishant-ydv/foxtrot/main/LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-000000?style=for-the-badge" alt="License">
  </a>
  <a href="https://foxtrotpilot.streamlit.app/">
    <img src="https://img.shields.io/badge/Streamlit-FF4B4A?style=for-the-badge&logo=streamlit" alt="Streamlit">
  </a>
</p>

<p align="center">
  <b>AI-powered inventory policy optimization for retail Category Business Owners</b><br>
  Translate budget + service goals into optimal inventory configs in seconds, not hours.
</p>

---

## The Problem

At large retailers, inventory policies (safety stock, DCC/service levels, reorder points) are defined entirely in **Excel**. Each "what-if" scenario takes **hours**, so teams explore 2–3 scenarios when **20+ should** be evaluated.

> On a $100M budget, suboptimal policies cost **$3–5M per cycle** in avoidable markdowns and lost sales.

Internal data science teams have simulations that show what configs *do* downstream — but no tool answers the upstream question:

> **"Given my budget and goals, what should the configs *be*?"**

---

## The Solution

Foxtrot translates budget + service-level goals into optimal inventory configurations across item segments (A/B/C/R), enabling instant scenario exploration that currently takes hours in Excel.

| Feature | Description |
|---------|-------------|
| **Budget → Policy** | Drop in budget + target service level → get optimal DCC, safety stock, allocation splits |
| **Instant Scenarios** | Natural language input: *"What if we cut budget by 20%?"* — see policy changes instantly |
| **LLM Narration** | Business-language trade-off analysis: why the policy changed, what risks emerged |
| **Decision Center** | Mid-season chase/abandon decisions with quantified trade-offs |
| **Segment Strategy** | R-items protected (always in stock), A-items prioritized, B/C optimized for efficiency |

---

## Live App

**Try it now:** https://foxtrotpilot.streamlit.app/

<p align="center">
  <a href="https://foxtrotpilot.streamlit.app/">
    <img src="https://img.shields.io/badge/🚀%20Try%20Live%20App-2ea32a?style=for-the-badge&logo=streamlit" alt="Try Live App">
  </a>
</p>

---

## Quick Start

### Prerequisites
- Python 3.10+
- Anthropic API key (or OpenRouter key for free models)

### Local Development

```bash
# Clone the repo
git clone https://github.com/nishant-ydv/foxtrot.git
cd foxtrot

# Set up environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Install dependencies
cd frontend
pip install -r requirements.txt

# Run the app
streamlit run app.py --server.port 8501
```

Open http://localhost:8501 in your browser.

### Streamlit Cloud Deployment

1. Push your fork to GitHub
2. Go to https://streamlit.io/cloud
3. Deploy with:
   - **Main file:** `frontend/app.py`
   - **Requirements:** `frontend/requirements.txt`
4. Add your API key in **Streamlit Secrets**:
   ```toml
   anthropic_api_key = "sk-..."
   anthropic_base_url = "https://openrouter.ai/api"
   anthropic_model = "tencent/hy3-preview:free"
   ```

---

## Architecture

```
Foxtrot/
├── backend/
│   ├── main.py            # FastAPI (optional backend server)
│   ├── optimizer.py       # OR-Tools unconstrained optimizer
│   ├── optimizer_simple.py # Pure Python fallback (Streamlit Cloud)
│   ├── llm_layer.py       # Anthropic Claude integration
│   ├── models.py          # Pydantic request/response models
│   └── data/
│       ├── demand/        # Per-department demand forecasts
│       ├── segments.json   # A/B/C/R segment definitions
│       └── vendors.json   # Vendor lead times, MOQs
│
└── frontend/
    ├── app.py            # Streamlit app — CBO-facing UI
    └── requirements.txt   # Dependencies (ortools, anthropic, streamlit)
```

### Three-Layer Architecture

| Layer | Purpose | Tech |
|-------|---------|-----|
| **Optimization Engine** | Computes optimal inventory policies (DCC, safety stock, allocation splits) given budget + service target | OR-Tools / Pure Python heuristic |
| **Scenario Simulation** | ML-powered what-if analysis: budget changes, service shifts, demand shocks | `scipy.stats` (inverse normal CDF) |
| **LLM Layer** | Translates business intent → optimization parameters, narrates trade-offs, frames decisions | Anthropic Claude (via OpenRouter) |

---

## Key Concepts

| Term | Meaning |
|------|---------|
| **CBO** | Category Business Owner — primary user, owns P&L for a department |
| **DCC** | Demand-Curve Coverage — identical to service level / in-stock % |
| **WIP** | Walk-In Purchasability — the customer experience of finding items in stock |
| **A/B/C/R** | Item tiers: A=high velocity, B=mid, C=low, R=reliability (must always be in stock) |
| **OTB** | Open-to-Buy: `Planned Sales + Markdowns + End Inventory - Beginning Inventory - On-Order` |

---

## Competitive Moat

No incumbent or startup offers **natural language scenario exploration** at the CBO's "budget → policy" altitude.

| Threat | Status |
|--------|--------|
| **RELEX** | Closest threat (12–18 month horizon) |
| **Blue Yonder / Oracle** | Downstream — Foxtrot is *upstream* of these systems |

**Foxtrot wins on:**
- CBO-centric UX (not planner-centric)
- LLM-powered intent translation
- Instant what-if at strategy level
- **Days to pilot** vs. 12–18 month enterprise implementations

---

## Documentation

| Document | Purpose |
|----------|---------|
| [Executive Problem Statement](Executive%20Problem%20Statement.md) | Concise problem statement for leadership/investors |
| [Problem Reframe & Workflow Map](Problem%20Reframe%20&%20Workflow%20Map.md) | Validated 12-step user workflow, pain points #1–#7 |
| [AI Layer Defense](AI%20Layer%20Defense.md) | Three-layer architecture with ML/LLM justification |
| [Competitive Landscape](Competitive%20Landscape.md) | Tier 1–3 competitive analysis |

---

## Status

**V0 — Core optimizer and Streamlit frontend working. Deployable to Streamlit Cloud.**

- [x] Unconstrained optimizer (feasible + infeasible paths)
- [x] Streamlit Cloud deployment (pure Python fallback)
- [x] Natural language scenario input
- [x] LLM narration (trade-off analysis)
- [x] Insufficient budget handling (3 options: increase, lower, keep)
- [x] Segment-level policy display (DCC, safety stock, allocations)
- [ ] SKU-level policy details (in progress)
- [ ] Mid-season decision center (next)

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  <b>Built for retail Category Business Owners who want answers, not spreadsheets.</b><br>
  <a href="https://foxtrotpilot.streamlit.app/">Try Foxtrot Live →</a>
</p>
