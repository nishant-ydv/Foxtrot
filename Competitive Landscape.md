# Competitive Landscape & Why We Win

## The Market Map

The inventory planning space has three tiers of players. Each tier solves a different slice of the problem. None solves ours.

---

## Tier 1 — Enterprise Incumbents (The Gorillas)

### Blue Yonder (Luminate Planning)
- **What they do:** End-to-end supply chain planning + execution. Multi-echelon inventory optimization (MEIO), AI-powered demand sensing, autonomous replenishment. In 2025 they launched "AI Agents" (Inventory Ops Agent) for exception management.
- **Scenario capability:** Yes — they have scenario analysis that "reduces planning from days to minutes." Uses digital twin simulation.
- **Where they fall short for our problem:**
  - Optimizes at SKU-Location level for *replenishment*, not at the CBO's strategic "budget → policy" level
  - Scenario exploration exists but is embedded in a massive, complex platform — a CBO doesn't use Blue Yonder directly; a planner does, and even they find the learning curve steep
  - No natural-language "what if my budget drops $3M — where's the best place to cut?" interaction
  - Implementation: 12-18 months, $1M+ cost, requires dedicated IT team
- **Verdict:** They own execution-level optimization. They don't own the CBO's strategic decision surface.

### Oracle Retail (RPAS / Planning Cloud)
- **What they do:** Merchandise financial planning, assortment planning, demand forecasting. Deep retailer install base.
- **Scenario capability:** Limited what-if in RPAS, but rigid — users report high click-counts, restrictive reporting, need for specialized expertise to modify
- **Where they fall short:** Same as Blue Yonder — planner-facing, execution-oriented, not a CBO decision tool. Customization requires vendor assistance. No LLM layer.
- **Verdict:** Legacy incumbent. Strong in execution. Weak in interactive strategic planning.

### Anaplan
- **What they do:** Connected planning platform. Multidimensional modeling, real-time what-if, collaborative cloud-based planning. Used across finance + supply chain.
- **Scenario capability:** **Strong** — this is their core value prop. Real-time scenario modeling, instant what-if, PlanIQ for AI-driven forecasting.
- **Where they fall short:**
  - Anaplan is a *platform*, not a *solution*. You build your own models. A retailer using Anaplan for inventory planning has to design and maintain the optimization logic themselves.
  - No built-in retail inventory optimization (safety stock, DCC, OTB). It's a general-purpose planning canvas.
  - No LLM layer — no natural language scenario exploration
  - No decision-framing for high-stakes calls (chase/abandon)
  - Expensive: $100K-$500K+ annually
- **Verdict:** Closest to our scenario exploration capability, but it's a blank canvas, not a purpose-built retail inventory decision tool. They solve "how do I model things" not "what should my inventory policy be."

### Kinaxis (RapidResponse + Maestro)
- **What they do:** Concurrent planning — real-time ripple-effect simulation across the supply chain. Sandbox environments for what-if. AI/ML via Maestro for predictive insights.
- **Scenario capability:** **Strong** — sandbox scenarios, automatic propagation of changes across network, side-by-side comparison.
- **Where they fall short:**
  - Designed for supply chain planners, not CBOs. Interface is technical.
  - Scenarios are network-wide (suppliers → DC → stores), not focused on the CBO's "budget + service level → policy" question
  - No natural language interaction
  - Heavy enterprise implementation
- **Verdict:** Best scenario tech among incumbents, but optimized for supply chain network planning, not CBO-level budget-to-policy decisions.

---

## Tier 2 — Growth-Stage Challengers

### RELEX Solutions
- **What they do:** AI-native unified retail planning. Automated replenishment, dynamic safety stock, digital twin, markdown/promotion optimization.
- **Scenario capability:** Digital twin modeling, confidence scoring, strategic goal alignment. Claims to translate "service levels and working capital targets into actionable plans."
- **Where they fall short:**
  - Closest competitor to our positioning — they claim "strategic goal alignment" and "scenario modeling"
  - But: still primarily a replenishment/execution platform. The scenario modeling is around supply chain operations, not "given this budget and WIP target, what's my optimal policy across segments?"
  - No LLM layer for natural language exploration
  - Heavy implementation, enterprise sales cycle
- **Verdict:** ⚠️ **Most dangerous competitor.** If they build a CBO-facing "budget → policy" module with LLM interaction, they could close the gap. But today they're focused on replenishment automation.

### o9 Solutions
- **What they do:** AI-powered integrated business planning. Digital brain concept — connects demand, supply, commercial, and financial planning.
- **Scenario capability:** Marketed heavily. "Enterprise knowledge graph" for scenario analysis.
- **Where they fall short:**
  - Broad platform covering everything from demand to S&OP to revenue management
  - Not focused specifically on inventory policy optimization for retail CBOs
  - High complexity, enterprise-grade implementation
- **Verdict:** Broad platform play. Could theoretically address this, but spread across too many use cases to be purpose-built for our problem.

---

## Tier 3 — AI-Native Startups (The New Wave)

### ManoloAI (Ariel)
- **What they do:** Agentic AI for procurement — autonomous vendor onboarding (80% reduction in effort), pricing analysis, spend intelligence, RFP generation, dead-SKU identification
- **Scenario capability:** None for inventory policy
- **Where they fall short:** 100% downstream — procurement and vendor operations. No planning, no scenario exploration, no budget-to-policy.
- **Verdict:** Different problem. Not a competitor.

### Lumari
- **What they do:** AI digital workers for procurement automation — RFQs, POs, supplier communications
- **Scenario capability:** None
- **Where they fall short:** Even more narrowly scoped than ManoloAI — pure procurement document automation.
- **Verdict:** Not a competitor. Adjacent space.

### Ovlo
- **What they do:** No-code AI agent platform for supply chain. Document processing (invoices, POs, compliance), reconciliation, demand forecasting, exception routing. Integrates with ERPs.
- **Scenario capability:** Has demand forecasting but no scenario exploration for inventory policy
- **Where they fall short:** Operational automation layer on top of ERPs. No strategic planning, no budget-to-policy, no decision framing.
- **Verdict:** Not a competitor. They automate the plumbing; we solve the strategy.

### Project Argus
- **What they do:** Supply chain visibility/control tower. Real-time inventory tracking, predictive delay detection, dynamic reallocation.
- **Scenario capability:** Predictive (what will happen) but not prescriptive (what should we set policies to)
- **Where they fall short:** Visibility and execution monitoring, not strategic planning.
- **Verdict:** Not a competitor. Complementary.

---

## The Gap Map — What the Business Needs vs. What Exists

| What the CBO Actually Needs | Blue Yonder | Oracle | Anaplan | Kinaxis | RELEX | AI Startups | **Us** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **"Budget + WIP target → optimal policy"** | ❌ | ❌ | ⚠️ Build-your-own | ❌ | ⚠️ Partial | ❌ | ✅ |
| **Instant what-if at budget↔service-level level** | ⚠️ Slow/complex | ❌ | ✅ Generic | ✅ Network-level | ⚠️ Replenishment-level | ❌ | ✅ Purpose-built |
| **Natural language scenario exploration** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **"Cut $3M — show me the least-damaging option"** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **High-stakes decision framing with quantified trade-offs** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **CBO-level interface (not planner-level)** | ❌ | ❌ | ⚠️ Configurable | ❌ | ❌ | ❌ | ✅ |
| **Item segment-aware optimization (A/B/C/R)** | ✅ | ✅ | ⚠️ Build-your-own | ✅ | ✅ | ❌ | ✅ |
| **Mid-season re-planning at low cost** | ❌ | ❌ | ⚠️ Possible | ⚠️ Possible | ❌ | ❌ | ✅ |
| **Auto-execute basic configs, surface high-stakes for approval** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Implementation in days, not months** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |

---

## Why We Actually Win — The Honest Case

### 1. We're solving for a different user
Everyone else builds for **planners and supply chain analysts**. We build for the **Category Business Owner** — the person who sets the strategy, owns the P&L, and makes the $100M calls. This is a different product with different UX, different language, and different success metrics.

### 2. We're solving at a different altitude
Everyone else optimizes at the **parameter level** (what should safety stock be for SKU X at store Y?). We optimize at the **strategy level** (given my budget and goals, what should my *entire* policy framework look like across all segments, seasons, and scenarios?).

### 3. The LLM layer is genuinely new
No incumbent or startup offers **natural language scenario exploration** for inventory planning. "What if holiday demand is 20% hotter and I need to cut $3M?" → three ranked options in 10 seconds. This interaction model didn't exist 2 years ago.

### 4. We can be complementary, not competitive
We don't replace Blue Yonder or Oracle. We sit **upstream** — we produce the policy that gets pushed *into* those systems. This means:
- No rip-and-replace required
- We can integrate with whatever execution layer the retailer already has
- We reduce friction in the sales process ("we work with your existing tools")

### 5. Speed to value
Incumbents: 12-18 month implementation, $1M+ cost. We: days to pilot, value on day one. For a startup assignment, this is especially critical — we can demo immediate value, not a roadmap.

---

## Threats to Take Seriously

| Threat | Likelihood | Severity | Our Response |
|---|:---:|:---:|---|
| **RELEX builds a CBO-facing "budget → policy" module** | 🟡 Medium (12-18 months) | 🔴 High | Move fast. Our LLM + UX moat buys time. They'd still lack natural language interaction. |
| **Anaplan customer builds this exact workflow on Anaplan** | 🟡 Medium | 🟡 Medium | We're purpose-built; they're DIY. Our product includes the optimization logic + LLM; Anaplan is just the canvas. |
| **Blue Yonder's AI Agents expand upstream into policy** | 🔴 Low (they're focused on execution) | 🔴 High | Differentiate on UX, speed, CBO-centricity. BY will always be planner-first. |
| **A new startup appears with the same thesis** | 🟡 Medium | 🟡 Medium | Domain expertise + speed of execution. First-mover with real retail practitioner insight wins. |

---

## The One-Liner Positioning

> **We're the strategic planning layer that sits between the CBO's goals and the enterprise execution systems — making $100M inventory decisions explorable, quantifiable, and reversible instead of rigid, opaque, and one-shot.**
