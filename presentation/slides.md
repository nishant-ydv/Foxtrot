# Slide 1: The Hook — $11-31M Preventable Loss

**Title:** Foxtrot: AI-Powered Inventory Policy Optimization

**Main Metric:**
- **$11-31M preventable loss** per $100M budget per cycle

**Secondary Metric:**
- Industry benchmark: 3-5% efficiency gain = **$3-5M** on $100M
- Preventing just **20-30%** of $11-31M = **$2-9M** achievable per cycle

**Subtitle:** "At large retailers, inventory policies that control $100M+ automated spending are defined in Excel"

**Speaker notes:**
Start with the big number: $11-31M preventable loss per cycle.
Industry benchmarks say 3-5% efficiency gain is achievable = $3-5M.
If we prevent just 20-30% of the preventable loss, that's $2-9M per department per cycle.
The root cause: policies are set in Excel. Teams explore 2-3 scenarios when 20+ should be evaluated.

---

# Slide 2: The Bottleneck — Why Excel Is Failing

**Heading:** The Bottleneck: Why Excel Is Failing

**Left Column: Validated Workflow Breakdown**
- 50% keyboard work (Excel)
- 30% coordination (Finance ↔ Planner)
- 20% approvals

**Key Stat:** 2-3 scenarios explored when 20+ should be evaluated

**Right Column: Pain Points (Validated)**
1. Scenario = 4 hours each
2. Budget trade-offs are blind
3. Mid-season decisions w/o data

**12-Step Workflow — Where It Breaks:**
```
[1. Trigger] [2. Goal Setting] [3. Demand Intake] [4. Vendor Input]
[🔴5. First-Pass Plan (Excel, 12-20 tabs)]
[🟡6. Budget Reconciliation] [🟡7. Approval Loop] [🟡8. Plan Finalization]
[🟢9. System Config] [🟢10. Execution]
[🔵11. Mid-Season Review] [🔴12. Re-plan (rarely done = $losses)]
```
- 🔴 RED = Excel bottleneck (4 hrs/scenario)
- 🟡 YELLOW = Coordination loop (weeks)
- 🟢 GREEN = Auto-execute
- 🔵 BLUE = High-stakes (needs data)

**Speaker notes:**
Steps 5, 6-8, and 12 are where Excel fails.
Step 5: Planner builds policy in Excel with 12-20 tabs. Each scenario = 4 hours.
Steps 6-8: Finance pushes back, planner reworks. 30% of time is coordination.
Step 12: Mid-season re-plan has same cost as original. Most teams absorb losses rather than re-plan.
The CBO owns P&L but approves plans they can't fully validate.

---

# Slide 3: The Solution — Foxtrot V0

**Heading:** The Solution: Foxtrot V0

**Positioning Statement:**
> Sits upstream of existing simulations and replenishment systems — figures out what the configs SHOULD be

**Left Column: Two-Tier Execution**
- **Basic configs (auto-execute):** DCC, safety stock %, allocation splits
- **High-stakes decisions (human):** Chase/abandon calls, mid-season pivots

**Right Column: Three-Layer Architecture**
1. **Optimization Engine** (OR-Tools) — computes optimal configs
2. **Scenario Layer** — instant what-if exploration
3. **LLM Layer** (Claude) — translates business intent ↔ math

**Architecture Flow:**
```
[CBO Browser] → [Foxtrot API] → [Optimizer (OR-Tools)]
                                      ↓
                              [LLM (Claude)]
                                      ↓
                              [Data/Configs]
                                      → [Replenishment System]
```

**Speaker notes:**
We're not building another simulation. We're building the step that comes BEFORE.
Two-tier: auto-execute routine configs, surface high-stakes for human decision.
Three layers: OR-Tools for math, Scenario layer for what-if, LLM for business language translation.
The CBO makes the decisions, not the AI.

---

# Slide 4: V0 Prototype — What It Unlocks

**Heading:** V0 Prototype: What's Built & What It Unlocks

**The 5 Key Unlocks:**

> ⚡ **Speed:** "What took 4 hours in Excel now takes 10 seconds" — scenario exploration bottleneck eliminated

> 🎯 **Infeasibility Handling:** Budget insufficient? Get 3 actionable options instantly (Increase, Keep & Show, Lower Target) — no more blind budget cuts

> 💬 **Natural Language:** "What if budget drops $3M?" — LLM translates business intent to parameter changes + narrates trade-offs in plain English

> 📊 **Decision Framing:** Mid-season crisis? Get $quantified options with upside/downside — CBO decides with data, not gut feel

> 🔍 **SKU + Segment Views:** Drill from segment-level (A/B/C/R) down to individual SKU configs — full transparency

**Result:** CBOs explore 20+ scenarios in the time it took to do 2-3 in Excel

**Speaker notes:**
It's not just "10 seconds vs 4 hours" — that's the speed unlock, but there are 4 other major unlocks:
1. Infeasibility handling: Foxtrot tells you exactly what's needed + 3 options
2. Natural language: Type scenarios, get instant policy changes + LLM narration
3. Decision framing: Mid-season crisis? Get quantified options with $
4. SKU-level transparency: See configs at segment level or drill down to individual SKUs
The demo will show all of these.

---

# Slide 5: Technical Architecture Deep Dive

**Heading:** Technical Architecture: V0 Deep Dive

**Actual V0 Architecture (Standalone Mode — what's deployed):**
```
[Streamlit UI]
    ↓ imports directly
[optimizer.py] → OR-Tools Optimizer
[llm_layer.py] → Claude LLM (via OpenRouter)
    ↓ reads
[JSON Data Store]
    ↓ optional
[FastAPI] (fallback if imports fail)
```

**Tech Stack & Rationale (Grid):**
| Technology | Rationale |
|-----------|----------|
| **OR-Tools** | Google's constraint optimizer — transparent math, not black-box ML |
| **Streamlit** | Python-native, Streamlit Cloud, standalone mode (no server needed) |
| **Claude via OpenRouter** | Best-in-class reasoning for business language, fallback chain |
| **FastAPI (optional)** | Lightweight REST API — used only in non-standalone mode |

**Key Design Decisions:**
- Standalone mode: Frontend imports backend directly — no separate server needed for Streamlit Cloud
- Unconstrained approach: "Given budget + target → what does it cost?"
- LLM as translator, not decision-maker (CBO always in control)
- JSON data store in V0 (swaps to PostgreSQL in V1)

**Speaker notes:**
This isn't a black-box ML product. The optimizer is transparent OR-Tools math.
V0's key design: Streamlit frontend imports backend modules directly in standalone mode.
FastAPI is optional — only used if local imports fail (API mode with separate backend server).
Claude (via OpenRouter) translates business language to parameters and narrates trade-offs.
JSON data store in V0 for speed — swaps to PostgreSQL in V1.
Key design: LLM as translator, not decision-maker. CBO always in control.
V0 is built by 1 developer. The architecture is designed to scale.

---

# Slide 6: V0 → V1 → V2: All Within One Quarter

**Heading:** V0 → V1 → V2: All Within One Quarter (3 Months)

**Timeline (No Overlaps):**

| Phase | Status | Timing | Key Features |
|-------|--------|--------|--------------|
| **V0 (Current)** | ✅ Done | Complete | Single-user, file-based, OR-Tools, Claude, Streamlit, core workflow |
| **V1 (Next)** | 🎯 Build | Month 1-2 | Multi-user + SSO, PostgreSQL, ERP/PO integration, policy approval, dynamic segmentation |
| **V2 (Final)** | 🚀 Build | Month 3 | Multi-dept optimization, cross-cycle learning, mobile app, bidirectional sim integration |

**V1 Details (Month 1-2):**
- Multi-user with SSO (Okta/Auth0)
- PostgreSQL database (audit trails, versioning)
- Real data integration (APIs to Demand/ERP systems)
- Policy approval workflow → Kafka → internal PO system
- Dynamic segmentation (10-20% items shift quarterly)
- Mid-season re-optimization (low-cost, fast)

**V2 Details (Month 3):**
- Multi-department budget allocation optimization
- Cross-cycle learning (institutional memory)
- Mobile app for mid-season decisions
- Integration with existing simulations (bidirectional)

**Competitive Context:** RELEX is 12-18 months away from CBO-centric UX + LLM-powered intent translation. Foxtrot V0 already demonstrates both. The entire roadmap fits within **one quarter (3 months)**.

**Speaker notes:**
V0 is done — proven prototype built by 1 developer.
V1 (Month 1-2): Enterprise features. PostgreSQL, SSO, real API integrations, policy push to internal PO system via Kafka.
V2 (Month 3): Platform features. Multi-department optimization, cross-cycle learning, mobile app.
Total roadmap: 3 months. Not 12+ months — everything fits within one quarter.
The competitive window is now. RELEX is 12-18 months behind on CBO-centric UX and LLM integration.

---

# Slide 7: What It Takes to Build V1 → V2

**Heading:** What It Takes to Build V1 → V2

**Left Column: Team & Timeline**
- **Timeline:** ~3 months total (V1: 1-2, V2: Month 3)
- **2-3 Engineers** (backend, frontend, data/integration)
- **1 Designer** (CBO-centric UX)
- **Optional:** 1 PM (roadmap, stakeholder coordination)

**Infrastructure:**
- Cloud (AWS/GCP) + enterprise security
- ~$5-10K/month cloud + LLM API costs

**Right Column: Key Work Streams**

**V1 (Month 1-2):**
- JSON → PostgreSQL (audit, versioning, multi-user)
- SSO (Okta/Auth0)
- ERP read + PO system write (Kafka)
- Auto-execute basic configs, surface high-stakes for sign-off
- Dynamic A/B/C/R segmentation

**V2 (Month 3):**
- Multi-department budget allocation
- Cross-cycle institutional memory
- Mobile app for mid-season decisions

**Closing Statement:**
> "V0 is a proven prototype built by a single developer. V1→V2 needs ~3-4 people and 3 months. The core optimization engine is already built and validated — V1-V2 is about enterprise integration, multi-user support, and production-grade reliability. All within one quarter."

**Speaker notes:**
V0 is built by 1 developer. V1 needs ~3-4 people and 1-2 months. V2 is another 1 month. Total: 3 months.
The core optimization engine is already built and validated — V1-V2 is about enterprise integration, multi-user support, and production-grade reliability.
Team: 2-3 engineers, 1 designer, optional PM.
Infrastructure: ~$5-10K/month cloud + LLM API costs.
The competitive window is now. RELEX won't have this capability for 12-18 months.
This is an assignment submission demonstrating what's possible and what it takes to ship.

---

# Demo Video Script Summary

**Duration:** 3-4 minutes

| Time | Segment | Key Action |
|------|---------|-------------|
| 0:00-0:30 | The Problem | Show Excel workbook with 12 tabs, 4 hours per scenario |
| 0:30-1:00 | Foxtrot Intro | Select dept, set budget+target, click Optimize |
| 1:00-1:45 | Infeasibility Flow | Budget insufficient → 3 options → click "Increase Budget" |
| 1:45-2:30 | Scenario Exploration | Type "What if budget drops $3M?" → instant results |
| 2:30-3:15 | Decision Framing | "Underforecasted by 20%" → options with $ upside/downside |
| 3:15-3:45 | V1 Teaser | Roadmap: multi-user, real data, downstream system push |

**Key Metrics to Emphasize:**
- "4 hours → 10 seconds"
- "$3-5M per $100M budget per cycle" (industry benchmark)
- "2-3 scenarios → 20+ scenarios"
- "V0 built by 1 developer in weeks"
- "RELEX is 12-18 months behind"
- "Entire roadmap: 3 months (one quarter)"

**Full script:** See `demo_video_script.md`
