"""LLM Layer — LLM integration for Foxtrot."""
import os
import json
import re
import sys
from typing import Dict, Any, List, Optional

MODEL_PRIMARY = os.getenv("ANTHROPIC_MODEL", "tencent/hy3-preview:free")
MODEL_FALLBACK = os.getenv("ANTHROPIC_FALLBACK_MODEL", "openai/gpt-oss-120b:free")
MODELS = [MODEL_PRIMARY, MODEL_FALLBACK]

_client = None

def _get_client():
    """Lazily initialize Anthropic client — reads env vars at call time (Streamlit Cloud compatible)."""
    global _client
    if _client is not None:
        return _client
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        api_key = os.getenv("ANTHROPIC_AUTH_TOKEN", "").strip()
    base_url = os.getenv("ANTHROPIC_BASE_URL", "").strip()
    try:
        from anthropic import Anthropic
        _client = Anthropic(api_key=api_key, base_url=base_url if base_url else None) if api_key else None
    except ImportError:
        _client = None
    print(f"[LLM Layer] API_KEY: {bool(api_key)}, Client: {_client is not None}", file=sys.stderr)
    return _client

def filter_reasoning(text: str) -> str:
    """Remove reasoning traces, meta-commentary, and parenthetical notes from LLM output."""
    if not text:
        return text
    # Remove parenthetical reasoning like (has X, Y, Z) or (contains A, B)
    text = re.sub(r'\([^)]*(?:has|contains|includes)[^)]*\)', ' ', text)
    # Remove meta-commentary sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    noise_starts = ['wait', 'let me', 'got it', 'hmm', 'actually', 'first', 'now',
                    'that\'s', 'i need to', 'aligns with', 'based on']
    clean = []
    for s in sentences:
        s_clean = s.strip()
        if not s_clean:
            continue
        if any(s_clean.lower().startswith(n) for n in noise_starts):
            continue
        clean.append(s_clean)
    result = ' '.join(clean)
    # Remove self-analysis phrases mid-sentence
    result = re.sub(r'aligns with the policy change[^.]*\.', '', result, flags=re.IGNORECASE)
    result = re.sub(r'based on the policy change[^.]*\.', '', result, flags=re.IGNORECASE)
    return result.strip()

def _call_llm(system_prompt: str, user_prompt: str) -> str:
    """Call LLM with fallback chain and return ONLY text blocks (never thinking/reasoning)."""
    client = _get_client()
    if not client:
        return ""
    for model in MODELS:
        for attempt in range(3):
            try:
                response = client.messages.create(
                    model=model,
                    max_tokens=500,
                    temperature=0,
                    messages=[{"role": "user", "content": user_prompt}],
                    system=system_prompt
                )
                text_parts = []
                for block in response.content:
                    block_type = getattr(block, 'type', '')
                    if block_type == 'text':
                        text_parts.append(block.text)
                result = " ".join(text_parts).strip()
                if not result:
                    print(f"[LLM Layer] Model {model} returned empty, trying next...", file=sys.stderr)
                    break
                if len(result) > 300:
                    sentences = re.split(r'[.!?]\s+', result)
                    noise = ['wait', 'let me', 'got it', 'hmm', 'actually', 'first', 'now']
                    clean = [s.strip() for s in sentences if s.strip() and not any(s.lower().startswith(n) for n in noise)]
                    if clean:
                        return filter_reasoning('. '.join(clean[-3:]) + '.')
                    if len(sentences) > 3:
                        return '. '.join(sentences[-3:]) + '.'
                    return filter_reasoning(sentences[-1].strip() if sentences else result[:200])
                return filter_reasoning(result[:300])
            except Exception as e:
                is_rate_limit = '429' in str(e) or 'rate' in str(e).lower() or 'quota' in str(e).lower()
                if is_rate_limit and attempt < 2:
                    backoff = 2 ** attempt
                    print(f"[LLM Layer] Model {model} rate limited, retrying in {backoff}s (attempt {attempt+1}/3)...", file=sys.stderr)
                    import time
                    time.sleep(backoff)
                    continue
                print(f"[LLM Layer] Model {model} failed: {e}", file=sys.stderr)
                break
        else:
            continue
        break
    return ""

def parse_scenario(nl_input: str, current_policy: Dict[str, Any], budget: float, service_target: float) -> Dict[str, Any]:
    """Parse natural language scenario into optimizer parameter changes. Reject invalid inputs."""
    nl_lower = nl_input.lower().strip()

    # Empty string -> unknown (not invalid)
    if not nl_lower:
        return {"action": "unknown", "value": 0, "segments": ["all"], "reasoning": "Empty input"}

    # Reject invalid/non-sensical inputs
    invalid_kws = ["asdf", "yo bro", "weather", "sports", "personal"]
    if any(kw in nl_lower for kw in invalid_kws):
        return {
            "action": "invalid", "error": True,
            "guidance": "Describe a scenario: budget change, service target change, or demand change.",
            "reasoning": "Invalid input"
        }

    # Supply chain keywords -> invalid (belongs in High-Stakes Decision Center)
    supply_chain_kw = ["vendor", "supplier", "shipping", "transport", "delay", "unserviceable", "logistics", "lead time", "leadtime"]
    if any(kw in nl_lower for kw in supply_chain_kw):
        return {
            "action": "invalid", "error": True,
            "guidance": "Vendor/supply chain issues belong in the High-Stakes Decision Center.",
            "reasoning": "Input is supply chain issue"
        }

    result = {"action": "unknown", "value": 0, "segments": ["all"], "reasoning": "Parsed from input"}

    # Use word-boundary aware checks - handle plural forms like "drops", "increases"
    has_increase = re.search(r'\b(increases?|boosts?|raises?|double)\b', nl_lower)
    has_decrease = re.search(r'\b(decreases?|reduces?|cuts?|lowers?|drops?)\b', nl_lower)
    has_budget = "budget" in nl_lower or "spend" in nl_lower
    has_service = "service" in nl_lower or "target" in nl_lower or "dcc" in nl_lower
    has_demand = "demand" in nl_lower

    # Determine action
    if has_increase:
        if has_budget:
            result["action"] = "increase_budget"
        elif has_service:
            result["action"] = "increase_target"
        elif has_demand:
            result["action"] = "demand_change"
    elif has_decrease:
        if has_budget:
            result["action"] = "reduce_budget"
        elif has_service:
            result["action"] = "reduce_target"
        elif has_demand:
            result["action"] = "demand_change"
    elif has_demand:
        result["action"] = "demand_change"
    elif has_service:
        # Service target mentioned without increase/decrease - check if it's "X%" (set TO)
        svc_match = re.search(r'(\d+\.?\d*)\s*%', nl_input)
        if svc_match:
            val = float(svc_match.group(1))
            if val > service_target:
                result["action"] = "increase_target"
                result["value"] = val - service_target
            else:
                result["action"] = "reduce_target"
                result["value"] = service_target - val
            return result
    elif has_budget:
        # Budget mentioned without increase/decrease - check if it's "X" (set TO)
        bgt_match = re.search(r'(\d+\.?\d*)\s*([MKmk]?)', nl_input)
        if bgt_match:
            num_str, unit = bgt_match.groups()
            val = float(num_str)
            if unit.upper() == 'M':
                val = val * 1_000_000
            elif unit.upper() == 'K':
                val = val * 1_000
            elif val < 1000:
                val = val * 1_000_000  # Assume M
            if val > budget:
                result["action"] = "increase_budget"
                result["value"] = val - budget
            else:
                result["action"] = "reduce_budget"
                result["value"] = budget - val
            return result

    # Extract value based on action
    if result["action"] == "demand_change":
        # Check for "by X%" pattern first (e.g., "drops by 30%")
        pct_match = re.search(r'(increase|decrease|drops|drop|spike|spikes)\s+by\s+(\d+\.?\d*)\s*%', nl_lower)
        if pct_match:
            direction = pct_match.group(1)
            val = float(pct_match.group(2))
            if direction in ["increase", "spike", "spikes"]:
                result["value"] = 1.0 + val / 100.0
            else:
                result["value"] = 1.0 - val / 100.0
            return result
        # Check for multipliers
        if any(w in nl_lower for w in ["double", "2x", "twice", "two times"]):
            result["value"] = 2.0
        elif any(w in nl_lower for w in ["triple", "3x", "three times"]):
            result["value"] = 3.0
        elif any(w in nl_lower for w in ["half", "0.5x", "0.5", "in half"]):
            result["value"] = 0.5
        elif any(w in nl_lower for w in ["quarter", "0.25x", "0.25"]):
            result["value"] = 0.25
        else:
            pct_match = re.search(r'(increase|decrease|drops|drop|spike|spikes)\s+(\d+\.?\d*)\s*%', nl_lower)
            if pct_match:
                direction = pct_match.group(1)
                val = float(pct_match.group(2))
                if direction in ["increase", "spike", "spikes"]:
                    result["value"] = 1.0 + val / 100.0
                else:
                    result["value"] = 1.0 - val / 100.0
            else:
                mult_match = re.search(r'demand\s+(?:is\s+)?(\d+\.?\d*)', nl_lower)
                if mult_match:
                    result["value"] = float(mult_match.group(1))
                else:
                    result["value"] = 1.0
        return result

    # For budget/service changes: extract value
    if result["action"] in ["increase_budget", "reduce_budget", "increase_target", "reduce_target"]:
        # Pattern 1: "by X" or "drops X" (change BY X)
        # E.g., "increase budget by $10M", "budget drops $3M"
        by_match = re.search(r'(?:by|drops?)\s+\$?(\d+\.?\d*)\s*([MKmk%]?)', nl_lower)
        if by_match:
            val = float(by_match.group(1))
            unit = by_match.group(2)
            if unit.upper() == 'M':
                result["value"] = val * 1_000_000
            elif unit.upper() == 'K':
                result["value"] = val * 1_000
            elif unit == '%':
                # For service: "by 5%" means 5 percentage points
                # For budget: "by 500%" means 500% of current budget
                if "target" in result["action"]:
                    result["value"] = val
                else:
                    result["value"] = val / 100.0 * budget
            else:
                result["value"] = val * 1_000_000 if val < 1000 else val
            return result

        # Pattern 2: "to X%" (set TO X) - must be before bare "X%" pattern
        # E.g., "reduce service to 90%", "increase target to 98%"
        to_match = re.search(r'to\s+(\d+\.?\d*)\s*%', nl_lower)
        if to_match and result["action"] in ["increase_target", "reduce_target"]:
            val = float(to_match.group(1))
            if result["action"] == "increase_target":
                result["value"] = val - service_target
            else:
                result["value"] = service_target - val
            return result

        # Pattern 3: bare "X%" without "by" or "to" (e.g., "increase budget 500%")
        pct_match = re.search(r'(\d+\.?\d*)\s*%', nl_lower)
        if pct_match and not by_match and not to_match:
            val = float(pct_match.group(1))
            if "target" in result["action"]:
                result["value"] = val  # Percentage points
            else:
                result["value"] = val / 100.0 * budget  # Percentage of budget
            return result

        # Pattern 3: "to $X" or "budget X" (set TO X)
        # E.g., "budget 120" (meaning 120M)
        if result["action"] in ["increase_budget", "reduce_budget"]:
            to_match = re.search(r'to\s+\$?(\d+\.?\d*)\s*([MKmk]?)', nl_lower)
            if not to_match:
                to_match = re.search(r'^(\d+\.?\d*)\s*([MKmk]?)$', nl_input.strip())
            if not to_match:
                to_match = re.search(r'budget\s+(\d+\.?\d*)\s*([MKmk]?)', nl_lower)
            if to_match:
                val = float(to_match.group(1))
                unit = to_match.group(2)
                if unit.upper() == 'M':
                    val = val * 1_000_000
                elif unit.upper() == 'K':
                    val = val * 1_000
                elif val < 1000:
                    val = val * 1_000_000
                if result["action"] == "increase_budget":
                    result["value"] = val - budget
                else:
                    result["value"] = budget - val
                return result

        # Pattern 4: Handle "double" for service target
        if "double" in nl_lower and result["action"] in ["increase_target", "reduce_target"]:
            result["value"] = 100.0 - service_target  # Vague, use remaining to 100%
            return result

        # Pattern 5: "cut in half" or "half"
        if "in half" in nl_lower or ("half" in nl_lower and "budget" in nl_lower):
            result["value"] = budget * 0.5
            return result

    return result

def narrate_tradeoff(old_policy: Dict[str, Any], new_policy: Dict[str, Any], budget_change: float, service_change: float) -> str:
    """Generate business-language narration."""
    try:
        if abs(budget_change) < 1 and abs(service_change) < 0.1:
            return "No significant policy changes detected."
        changes = []
        if old_policy and new_policy:
            for seg in new_policy.get("configs", {}):
                if seg in old_policy.get("configs", {}):
                    old_cfg = old_policy["configs"][seg]
                    new_cfg = new_policy["configs"][seg]
                    dcc_change = new_cfg.get("dcc_pct", 0) - old_cfg.get("dcc_pct", 0)
                    if abs(dcc_change) > 0.1:
                        changes.append(f"{seg}: DCC {dcc_change:+.1f}%")
        system_prompt = """You are a retail strategy advisor. Write ONLY 2-3 sentences in business language."""
        user_prompt = f"""Policy change:
- Budget change: ${budget_change:+,.0f}
- Service change: {service_change:+.1f} pts
- Changes: {', '.join(changes) if changes else 'Minor adjustments'}
Write 2-3 sentences ONLY:"""
        text = _call_llm(system_prompt, user_prompt)
        return text if text else f"Service level {'improved' if service_change > 0 else 'maintained'} by {abs(service_change):.1f} pts. Budget impact: ${abs(budget_change):,.0f}."
    except Exception:
        return f"Service level {'improved' if service_change > 0 else 'maintained'} by {abs(service_change):.1f} pts."

def explain_infeasibility(budget: float, service_target: float, min_budget: float) -> str:
    """Explain budget infeasibility."""
    gap = min_budget - budget
    achievable = max(80.0, service_target * (budget / min_budget))
    try:
        system_prompt = """Explain budget infeasibility in 2-3 sentences. List 3 options."""
        user_prompt = f"""Budget: ${budget:,.0f}, Target: {service_target}%, Min needed: ${min_budget:,.0f}
Gap: ${gap:,.0f}. Achievable: ~{achievable:.1f}%.
Explain and list 3 options:"""
        return _call_llm(system_prompt, user_prompt)
    except Exception:
        return (f"Target {service_target}% not achievable with ${budget:,.0f}.\n"
                f"Min budget: ${min_budget:,.0f}. Achievable: ~{achievable:.1f}%.\n"
                f"Options: (1) Increase budget, (2) Lower target, (3) Keep budget.")

def _fallback_decision(decision_context: str, budget: float) -> Dict[str, Any]:
    """Smart fallback when LLM is unavailable -- use keywords to pick recommendation."""
    ctx = decision_context.lower().strip()

    # Reject empty input
    if not ctx:
        return {
            "options": [],
            "recommendation": "Invalid input",
            "error": True,
            "guidance": "Describe a mid-season issue: demand change, supply delay, inventory problem, or cost increase."
        }

    # Invalid input keywords
    invalid_kws = ["asdf", "yo bro", "weather", "sports", "personal"]
    if any(kw in ctx for kw in invalid_kws):
        return {
            "options": [],
            "recommendation": "Invalid input",
            "error": True,
            "guidance": "Describe a mid-season issue: demand change, supply delay, inventory problem, or cost increase."
        }

    # Overforecast: demand is LOWER than forecasted -> Hold
    hold_keywords = ["overforecast", "forecast high", "excess", "demand lower", "too high", "demand drop", "demand half"]
    # Underforecast: demand is HIGHER than forecasted -> Chase
    chase_keywords = ["underforecast", "shortage", "demand higher", "too low", "forecast drop", "forecast low", "demand spike"]

    is_hold = any(kw in ctx for kw in hold_keywords)
    is_chase = any(kw in ctx for kw in chase_keywords)

    # Supply chain issues -> Negotiate/Expedite
    supply_kws = ["vendor delay", "transport cost", "lead time", "supply chain", "shipping", "logistics", "material cost", "tariff"]
    # Inventory issues -> Hold/Markdown or Chase
    inventory_high = ["excess inventory", "too much inventory", "overstock"]
    inventory_low = ["running low", "stockout risk", "shortage"]

    is_supply = any(kw in ctx for kw in supply_kws)
    is_inv_high = any(kw in ctx for kw in inventory_high)
    is_inv_low = any(kw in ctx for kw in inventory_low)

    chase_up = budget * 0.02
    chase_down = budget * 0.03
    hold_down = budget * 0.05

    # Priority: over/underforecast > supply chain > inventory > default
    if is_hold and not is_chase:
        return {
            "options": [
                {"option": "Hold", "description": "Accept overforecast and adjust targets",
                 "upside": 0, "downside": -hold_down, "recommendation": True,
                 "explanation": f"Hold: Forecast was too high. Avoid excess inventory. Downside: -${hold_down/1_000_000:.1f}M."},
                {"option": "Chase", "description": "Place POs mid-season",
                 "upside": chase_up, "downside": -chase_down, "recommendation": False,
                 "explanation": f"Chase: Risky with overforecast. Upside: +${chase_up/1_000_000:.1f}M."}
            ],
            "recommendation": "Hold"
        }
    elif is_chase and not is_hold:
        return {
            "options": [
                {"option": "Chase", "description": "Place POs to meet actual demand",
                 "upside": chase_up, "downside": -chase_down, "recommendation": True,
                 "explanation": f"Chase: Forecast was too low. Increase purchasing. Upside: +${chase_up/1_000_000:.1f}M."},
                {"option": "Hold", "description": "Accept underforecast",
                 "upside": 0, "downside": -hold_down, "recommendation": False,
                 "explanation": f"Hold: Accept the miss. Downside: -${hold_down/1_000_000:.1f}M."}
            ],
            "recommendation": "Chase"
        }
    elif is_supply:
        # Lead time issues -> Expedite, others -> Negotiate
        if "lead time" in ctx:
            return {
                "options": [
                    {"option": "Expedite", "description": "Pay premium for faster delivery",
                     "upside": budget * 0.03, "downside": -budget * 0.04, "recommendation": True,
                     "explanation": f"Expedite: Faster delivery. Upside: +${budget*0.03/1_000_000:.1f}M if demand holds."},
                    {"option": "Negotiate", "description": "Negotiate with vendor",
                     "upside": budget * 0.01, "downside": -budget * 0.02, "recommendation": False,
                     "explanation": f"Negotiate: Try to reduce costs. Upside: +${budget*0.01/1_000_000:.1f}M."}
                ],
                "recommendation": "Expedite"
            }
        return {
            "options": [
                {"option": "Negotiate", "description": "Negotiate with vendor",
                 "upside": budget * 0.01, "downside": -budget * 0.02, "recommendation": True,
                 "explanation": f"Negotiate: Try to reduce costs. Upside: +${budget*0.01/1_000_000:.1f}M."},
                {"option": "Expedite", "description": "Pay premium for faster delivery",
                 "upside": budget * 0.03, "downside": -budget * 0.04, "recommendation": False,
                 "explanation": f"Expedite: Faster delivery. Upside: +${budget*0.03/1_000_000:.1f}M if demand holds."}
            ],
            "recommendation": "Negotiate"
        }
    elif is_inv_high:
        return {
            "options": [
                {"option": "Hold", "description": "Accept excess inventory",
                 "upside": 0, "downside": -hold_down, "recommendation": True,
                 "explanation": f"Hold: Excess inventory. Downside: -${hold_down/1_000_000:.1f}M."},
                {"option": "Markdown", "description": "Mark down to clear stock",
                 "upside": 0, "downside": -budget * 0.10, "recommendation": False,
                 "explanation": f"Markdown: Clear excess. Downside: -${budget*0.10/1_000_000:.1f}M."}
            ],
            "recommendation": "Hold"
        }
    elif is_inv_low:
        return {
            "options": [
                {"option": "Chase", "description": "Place POs to restock",
                 "upside": chase_up, "downside": -chase_down, "recommendation": True,
                 "explanation": f"Chase: Running low. Increase purchasing. Upside: +${chase_up/1_000_000:.1f}M."},
                {"option": "Hold", "description": "Accept stockout risk",
                 "upside": 0, "downside": -hold_down, "recommendation": False,
                 "explanation": f"Hold: Accept risk. Downside: -${hold_down/1_000_000:.1f}M."}
            ],
            "recommendation": "Chase"
        }
    else:
        # Default: Chase
        return {
            "options": [
                {"option": "Chase", "description": "Place POs mid-season",
                 "upside": chase_up, "downside": -chase_down, "recommendation": True,
                 "explanation": f"Chase: Increase purchasing. Upside: +${chase_up/1_000_000:.1f}M."},
                {"option": "Hold", "description": "Accept current situation",
                 "upside": 0, "downside": -hold_down, "recommendation": False,
                 "explanation": f"Hold: No action. Downside: -${hold_down/1_000_000:.1f}M."}
            ],
            "recommendation": "Chase"
        }

def frame_decision(decision_context: str, dept_id: int, budget: float, current_service: float) -> Dict[str, Any]:
    """Frame a high-stakes decision. Reject invalid inputs."""
    # Reject empty input
    if not decision_context or not decision_context.strip():
        return {
            "options": [],
            "recommendation": "Invalid input",
            "error": True,
            "guidance": "Describe a mid-season issue: demand change, supply delay, inventory problem, or cost increase."
        }
    # KEYWORD PRE-CHECK: Handle clear overforecast/underforecast cases directly
    ctx_lower = decision_context.lower()
    hold_kws = ["overforecast", "forecast high", "excess inventory", "too high", "demand lower", "demand drop", "demand half"]
    chase_kws = ["underforecast", "shortage", "demand higher", "too low", "forecast drop", "forecast low", "demand spike"]

    is_hold = any(kw in ctx_lower for kw in hold_kws)
    is_chase = any(kw in ctx_lower for kw in chase_kws)

    if is_hold and not is_chase:
        hold_down = budget * 0.05
        chase_up = budget * 0.02
        return {
            "options": [
                {"option": "Hold", "description": "Accept overforecast",
                 "upside": 0, "downside": -hold_down, "recommendation": True,
                 "explanation": f"Hold: Forecast too high. Downside: -${hold_down/1_000_000:.1f}M."},
                {"option": "Chase", "description": "Place POs mid-season",
                 "upside": chase_up, "downside": -budget * 0.03, "recommendation": False,
                 "explanation": f"Chase: Risky. Upside: +${chase_up/1_000_000:.1f}M."}
            ],
            "recommendation": "Hold"
        }
    elif is_chase and not is_hold:
        chase_up = budget * 0.02
        hold_down = budget * 0.05
        return {
            "options": [
                {"option": "Chase", "description": "Place POs to meet demand",
                 "upside": chase_up, "downside": -budget * 0.03, "recommendation": True,
                 "explanation": f"Chase: Forecast too low. Upside: +${chase_up/1_000_000:.1f}M."},
                {"option": "Hold", "description": "Accept underforecast",
                 "upside": 0, "downside": -hold_down, "recommendation": False,
                 "explanation": f"Hold: Accept miss. Downside: -${hold_down/1_000_000:.1f}M."}
            ],
            "recommendation": "Chase"
        }

    # If unclear, proceed to LLM
    if not _get_client():
        return _fallback_decision(decision_context, budget)

    system_prompt_validate = """You are a retail decision validator. Determine if input is valid mid-season decision context.
VALID: demand changes, supply chain issues, inventory issues, cost changes.
INVALID: non-sensical text, unrelated topics, vague requests.
Return JSON: {"valid": true} or {"valid": false, "guidance": "..."}"""
    user_prompt_validate = f"Context: {decision_context}\nJSON:"
    content = _call_llm(system_prompt_validate, user_prompt_validate)

    is_valid = True
    guidance = ""
    if "{" in content:
        try:
            json_start = content.index("{")
            json_end = content.rindex("}") + 1
            llm_result = json.loads(content[json_start:json_end])
            if not llm_result.get("valid", True):
                is_valid = False
                guidance = llm_result.get("guidance", "Describe a mid-season issue.")
        except Exception:
            pass

    if not is_valid:
        return {
            "options": [],
            "recommendation": "Invalid input",
            "error": True,
            "guidance": guidance
        }

    try:
        system_prompt = """YOU ARE A JSON GENERATOR. Output ONLY valid JSON.
FORMAT: {"options": [{"option": "...", "description": "...", "upside": float, "downside": float, "explanation": "..."}], "recommendation": "..."}
DECISION LOGIC:
- Overforecast (demand lower): recommend HOLD
- Underforecast (demand higher): recommend CHASE
- Supply chain: NEGOTIATE or EXPEDITE
- Excess inventory: HOLD or MARKDOWN
- Stockout risk: CHASE or EXPEDITE"""
        user_prompt = f"""Context: {decision_context}
State: Dept {dept_id}, Budget ${budget:,.0f}, Service {current_service}%
Respond JSON ONLY:"""

        content = _call_llm(system_prompt, user_prompt)
        if "{" in content:
            json_start = content.index("{")
            json_end = content.rindex("}") + 1
            result = json.loads(content[json_start:json_end])
            # Override LLM if it got Chase/Hold wrong
            is_hold = any(kw in ctx_lower for kw in ["overforecast", "forecast high", "excess", "demand lower", "too high"])
            is_chase = any(kw in ctx_lower for kw in ["underforecast", "shortage", "demand higher", "too low", "forecast drop", "forecast low"])
            if is_hold and not is_chase:
                if result.get("recommendation", "").lower() != "hold":
                    result["recommendation"] = "Hold"
                    for opt in result.get("options", []):
                        if opt.get("option", "").lower() == "hold":
                            opt["recommendation"] = True
                        else:
                            opt["recommendation"] = False
            elif is_chase and not is_hold:
                if result.get("recommendation", "").lower() != "chase":
                    result["recommendation"] = "Chase"
                    for opt in result.get("options", []):
                        if opt.get("option", "").lower() == "chase":
                            opt["recommendation"] = True
                        else:
                            opt["recommendation"] = False
            return result
        return _fallback_decision(decision_context, budget)
    except Exception:
        return _fallback_decision(decision_context, budget)
