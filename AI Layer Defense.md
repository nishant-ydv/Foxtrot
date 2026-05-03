# What's AI-Powered Here? — Defense Framework

## The Three Layers

**Layer 1 — Optimization Engine (Math/OR)**
Constrained optimization: budget + demand + lead times + segment rules → optimal safety stock, DCC, allocation splits. Classical operations research. Blue Yonder and o9 already do this. **Not "AI" in the modern sense — it's math.**

**Layer 2 — Scenario Simulation (Statistical/ML)**
Monte Carlo simulation of demand uncertainty, sensitivity analysis. Still mostly classical.

**Layer 3 — LLM Layer (The real AI value)**

| What the LLM does | Why it's not window dressing | Example |
|---|---|---|
| **Intent → Parameters** | CBO says business things, not math things. LLM translates. | "What if holiday demand is 20% hotter and vendor X is 2 weeks slower?" → maps to 4 parameter changes across 3 sub-categories, runs optimizer |
| **Trade-off narration** | Optimizer outputs numbers. CBO needs decisions. LLM bridges the gap. | Instead of "SS drops 30%→22% on B-items" → "You're accepting 3% higher stockout risk on mid-tier items to save $2.1M. Last cycle, similar settings caused ~4 stockout incidents." |
| **Decision framing** | Doesn't decide — structures the decision for the CBO. | "Underforecasted holiday by 20%. Option A: Chase — upside $3.2M, downside $4.1M salvage. Option B: Hold — miss $2.8M sales, protect margin. Chase worked 2/3 past holidays." |
| **Constraint synthesis** | Finance says "cut $3M." 50 ways to cut. LLM finds and ranks them. | "Option A: reduce DCC on C-items 93%→88%, saves $3.1M, stockout risk +2.4%. Option B: shift $3M pre-season→in-season. Option C: cut 15% safety stock on low-velocity items." |
| **Cross-cycle learning** | Institutional memory at scale. | "Last time you set 97% DCC for holiday, you ended with 8% excess. Demand looks similar this cycle. Consider 95% with mid-season reorder trigger." |

## The Core Framework

> **The optimizer computes. The LLM translates between business thinking and mathematical optimization.** Without the LLM, this is a faster spreadsheet. With it, it's a strategic planning co-pilot that absorbs the cognitive load of translating "97% WIP on $100M" into 50 interlinked parameter decisions and explains consequences in business language.

## The One-Liner

> "The optimization math is table stakes. The AI is the layer that lets a business owner say 'what if holiday is 20% hotter and I need to cut $3M' and get three ranked options with quantified trade-offs in 10 seconds — instead of 3 days of spreadsheet rework."
