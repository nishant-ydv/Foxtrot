# Foxtrot CPO Presentation Package

This folder contains everything needed for the CPO presentation.

## Files

### 1. `index.html` — HTML Slide Deck
**What:** Professional presentation built with Reveal.js  
**How to use:** Open directly in any browser (Chrome, Safari, Firefox)  
**Why:** No special software needed — just double-click or run `open index.html`  

**Features:**
- 7 slides matching the approved plan
- Speaker notes (press 'S' to view)
- Clean, professional design
- Works offline (uses CDN for Reveal.js)

**Keyboard shortcuts:**
- `→` / `←` — Navigate slides
- `S` — Speaker view (shows notes)
- `F` — Fullscreen
- `O` — Overview mode

---

### 2. `slides.md` — Markdown Slide Content
**What:** Same 7 slides in markdown format  
**How to use:** Copy-paste into Google Slides, PowerPoint, or Keynote  
**Why:** Most people prefer to use their own slide software  

**Instructions:**
1. Open `slides.md`
2. Copy each slide section
3. Paste into your slide deck
4. Apply your own formatting/template

---

### 3. `demo_video_script.md` — Demo Video Script
**What:** Detailed 3-4 minute demo video script with timestamps  
**How to use:** Use as a teleprompter while recording your screen  
**Why:** Ensures you cover all key features in the allotted time  

**Prerequisites for recording:**
- Streamlit Cloud deployed app (not localhost)
- Screen recording software (QuickTime, OBS, Loom)
- Microphone for voiceover
- Clean browser profile (no distractions)

**Timing breakdown:**
| Time | Segment |
|------|---------|
| 0:00-0:30 | The Problem |
| 0:30-1:00 | Foxtrot Intro |
| 1:00-1:45 | Infeasibility Flow |
| 1:45-2:30 | Scenario Exploration |
| 2:30-3:15 | Decision Framing |
| 3:15-3:45 | V1 Teaser |

---

## Quick Start

1. **Review the slides:** Open `index.html` in your browser
2. **Customize:** If needed, edit the HTML or use `slides.md` to create your own deck
3. **Practice the demo:** Use `demo_video_script.md` to rehearse the 3-4 min demo
4. **Record:** Once comfortable, record the demo video following the script

---

## Key Talking Points (Cheat Sheet)

**The Hook:**
- "3-5% efficiency improvement = $3-5M per $100M budget"
- "Teams explore 2-3 scenarios when 20+ should be evaluated"

**The Solution:**
- "We're upstream of simulations — we figure out what the configs SHOULD be"
- "10 seconds vs 4 hours"

**The Tech:**
- "OR-Tools math, not black-box ML"
- "Claude translates business language to parameters"
- "CBO always makes the decisions"

**The Ask (What it takes):**
- "V0 built by 1 developer"
- "V1 needs ~3-4 people and 3-4 months"
- "Core engine is done — V1 is integration + scale"

**The Competitive Edge:**
- "RELEX is 12-18 months behind on CBO-centric UX + LLM"
- "The competitive window is now"
