# Foxtrot V0 Demo Video Script

**Duration:** 3-4 minutes  
**Format:** Screen recording with voiceover  
**Prerequisites:** Streamlit Cloud deployed app (not localhost) for professional look

---

## 0:00-0:30 — The Problem

**Screen:** Show an Excel icon or screenshot of a multi-tab spreadsheet (can use a generic image)

**Voiceover:**
> "At large retailers, Category Business Owners set inventory policies that control automated spending for an entire season. The problem? These policies are defined entirely in Excel. Here's what a planner's workbook looks like — 12 to 20 tabs, complex formulas, manual scenario calculations. Each 'what if' scenario takes 4 hours. Teams explore 2-3 scenarios when 20+ should be evaluated. On a $100M budget, this leads to $3-5M in preventable margin loss per cycle."

**Action:** Show a simple text overlay: `"4 hours per scenario" → "2-3 scenarios" → "$3-5M loss"`

---

## 0:30-1:00 — Foxtrot Intro

**Screen:** Open the deployed Streamlit app. Show the clean UI with department selector.

**Voiceover:**
> "This is Foxtrot. Let me show you how it works. I select a department — say, Men's Shoes, department 101. Set my budget to $100M, service target to 97%. Click 'Optimize Policy'. That's it."

**Action:**
1. Select department from dropdown
2. Type budget: 100 (meaning $100M)
3. Set service target slider to 97%
4. Click "Optimize Policy" button
5. Show the results appearing instantly

**Voiceover (continued):**
> "In 10 seconds, Foxtrot computes the optimal inventory policy across all item segments — A, B, C, and R — with DCC percentages, safety stock, reorder points, and allocation splits. What took 4 hours in Excel now takes 10 seconds."

---

## 1:00-1:45 — The Killer Feature: Infeasibility Handling

**Screen:** Change budget to $50M (clearly insufficient), click Optimize again.

**Voiceover:**
> "But here's where it gets interesting. What if my budget isn't enough? Let me drop the budget to $50M and optimize again."

**Action:**
1. Change budget to 50
2. Click Optimize
3. Show the red error box: "Budget Insufficient"
4. Point to the three options: "Increase Budget", "Keep & Show", "Lower Target"
5. Click "Increase Budget" — watch the budget auto-adjust

**Voiceover (continued):**
> "Foxtrot doesn't just say 'not enough budget.' It tells me exactly what I need — $87M minimum — and gives me three options. I can increase my budget, keep the current budget and see what's achievable, or lower my target. Let me click 'Increase Budget' — it instantly recalculates. This is the killer feature — instant feedback with actionable options."

---

## 1:45-2:30 — Natural Language Scenarios

**Screen:** Scroll down to "Scenario Explorer" section. Type a scenario in the text input.

**Voiceover:**
> "Now for the magic. Foxtrot has a Scenario Explorer that understands natural language. Let me type: 'What if budget drops $3M?' "

**Action:**
1. Type: "What if budget drops $3M?"
2. Click "Run Scenario"
3. Show the LLM narration appearing
4. Show the policy changes

**Voiceover (continued):**
> "The LLM layer translates my business question into parameter changes, re-optimizes the policy, and narrates the trade-offs in plain English. 'Service level maintained by reducing safety stock on C-items by 2.1%, saving $3M. Stockout risk increases marginally on low-priority items.' This is what teams couldn't do in Excel — instant what-if with business-language explanations."

**Action (bonus):**
1. Try another: "What if service target increases to 98%?"
2. Show the result

---

## 2:30-3:15 — High-Stakes Decision Framing

**Screen:** Scroll to "High-Stakes Decision Center" section.

**Voiceover:**
> "But what about mid-season crises? Demand spikes, supply chain disruptions, forecast errors. These are high-stakes moments where the CBO needs quantified trade-offs, not just numbers."

**Action:**
1. Type in Decision Context: "Underforecasted holiday by 20% for winter coats, 1 week left. Do we place POs?"
2. Click "Frame Decision"
3. Show the options with $ upside/downside
4. Point to the recommendation

**Voiceover (continued):**
> "I type the situation: 'Underforecasted holiday by 20%, 1 week left. Do we place POs?' Foxtrot frames the decision with quantified options. Option A: Chase demand — upside $2.1M if we're right, downside $3.2M if we're wrong. Option B: Hold course — miss $2.8M in sales. The system recommends: Chase. Each option has a clear financial explanation. The CBO decides — Foxtrot just structures the decision."

---

## 3:15-3:45 — V1 Teaser & Close

**Screen:** Show a slide or text overlay with the V0 → V1 roadmap (can use Slide 6 from the deck)

**Voiceover:**
> "Foxtrot V0 is a proven prototype, built by a single developer. It demonstrates the core value: 10-second policy optimization, natural language scenarios, and decision framing. V1 will add enterprise features — multi-user support, PostgreSQL database, real API integrations with your ERP systems, and automated policy push to your internal PO systems. The competitive window is now — RELEX won't have this CBO-centric UX with LLM-powered intent translation for another 12-18 months. Foxtrot is ready to own this space."

**Screen (final frame):**
- Text: "Foxtrot: From 4 hours to 10 seconds"
- Contact info / next steps

---

## Technical Notes

- **Record at 1080p** for professional quality
- **Use Streamlit Cloud** (not localhost) — shows the deployed, production-ready state
- **Clear browser cache** before recording — no personal bookmarks or notifications
- **Use a clean browser profile** — no distracting extensions or tabs
- **Voiceover pacing:** Pause briefly after each major point (3-5 seconds)
- **Zoom in** on key UI elements (the 3 options, the scenario input, the decision framing)
- **Cursor highlights:** Use mouse highlighting or cursor movements to guide viewer attention
- **Background:** Minimal, clean desktop — no personal files visible

## Optional: Live vs. Narated

**Option A: Live voiceover while recording** (recommended)
- More natural, can react to what's on screen
- Practice the script 2-3 times first

**Option B: Record screen first, add voiceover in editing**
- More polished, can re-record audio if needed
- Requires video editing software (iMovie, DaVinci Resolve, etc.)

## Key Metrics to Emphasize (Verbally)

- "4 hours → 10 seconds"
- "$3-5M per $100M budget per cycle"
- "2-3 scenarios → 20+ scenarios"
- "V0 built by 1 developer in weeks"
- "RELEX is 12-18 months behind"
