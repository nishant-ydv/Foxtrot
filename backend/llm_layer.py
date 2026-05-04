"""LLM Layer — LLM integration for Foxtrot."""
import os
import json
import re
from typing import Dict, Any, List, Optional

# Load .env file so API keys are available regardless of import order
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
    if os.path.exists(_env_path):
        load_dotenv(_env_path, override=True)
except ImportError:
    pass  # dotenv not installed; rely on environment variables

# Initialize Anthropic client (works with OpenRouter)
api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
if not api_key:
    api_key = os.getenv("ANTHROPIC_AUTH_TOKEN", "").strip()

base_url = os.getenv("ANTHROPIC_BASE_URL", "").strip()

try:
    from anthropic import Anthropic
    client = Anthropic(api_key=api_key, base_url=base_url if base_url else None) if api_key else None
except ImportError:
    client = None

MODEL_PRIMARY = os.getenv("ANTHROPIC_MODEL", "tencent/hy3-preview:free")
MODEL_FALLBACK = os.getenv("ANTHROPIC_FALLBACK_MODEL", "openai/gpt-oss-120b:free")
MODELS = [MODEL_PRIMARY, MODEL_FALLBACK]

import sys
print(f"[LLM Layer] API_KEY: {bool(api_key)}, Primary: {MODEL_PRIMARY}, Fallback: {MODEL_FALLBACK}, Client: {client is not None}", file=sys.stderr)
def filter_reasoning(text: str) -> str:
    """Remove reasoning traces, meta-commentary, and parenthetical notes from LLM output."""
    if not text:
        return text
    import re
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
                # Extract ONLY text blocks from response (ignore thinking/reasoning)
                text_parts = []
                for block in response.content:
                    block_type = getattr(block, 'type', '')
                    if block_type == 'text':
                        text_parts.append(block.text)

                result = " ".join(text_parts).strip()
                if not result:
                    print(f"[LLM Layer] Model {model} returned empty, trying next...", file=sys.stderr)
                    break  # Don't retry empty responses, go to next model

                # If result is too long (>300 chars), return last 2-3 sentences
                if len(result) > 300:
                    sentences = re.split(r'[.!?]\s+', result)
                    # Skip "thinking" sentences
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
    if not client:
        return {
            "action": "unknown",
            "value": 0,
            "segments": [],
            "reasoning": "LLM unavailable",
            "error": True
        }

    # First: strict LLM validation of input sensibility
    system_prompt = """You are a retail scenario validator. Determine if the input is a valid inventory policy scenario.

VALID inputs are ONLY about:
- Budget changes (increase/decrease by $XM, $XK, or X%)
- Service target changes (increase/decrease to X% or by X%)
- Lead time changes (double, increase by X weeks, etc.)
- Demand changes (increase/decrease by X%)

INVALID inputs include:
- Non-sensical text ("yo bro", "asdf", etc.)
- Unrelated topics (weather, sports, personal questions)
- Vague requests without numbers ("make it better")

Return ONLY this JSON, nothing else:
{"valid": true} for valid inputs
{"valid": false, "guidance": "..."} for invalid inputs (guidance: 1 sentence on what to ask)"""
    user_prompt = f"Input: {nl_input}\nJSON:"
    content = _call_llm(system_prompt, user_prompt)

    # Parse validation result
    is_valid = True
    guidance = ""
    if "{" in content:
        try:
            json_start = content.index("{")
            json_end = content.rindex("}") + 1
            llm_result = json.loads(content[json_start:json_end])
            if not llm_result.get("valid", True):
                is_valid = False
                guidance = llm_result.get("guidance", "Ask about budget, service target, lead time, or demand changes with specific numbers.")
        except Exception:
            pass  # If JSON parse fails, assume valid and continue to rule-based

    if not is_valid:
        return {
            "action": "invalid",
            "error": True,
            "guidance": guidance,
            "reasoning": "LLM validation: invalid input"
        }

    # Rule-based check: reject supply chain/vendor issues (belong in Decision Center)
    nl_lower = nl_input.lower()
    supply_chain_kw = ["vendor", "supplier", "shipping", "transport", "delay", "unserviceable", "logistics"]
    if any(kw in nl_lower for kw in supply_chain_kw):
        return {
            "action": "invalid",
            "error": True,
            "guidance": "Vendor/supply chain issues belong in the High-Stakes Decision Center, not Scenario Explorer. Scenario Explorer supports budget, service target, lead time, and demand changes.",
            "reasoning": "Input is supply chain issue, not scenario change"
        }

    # Rule-based parsing for valid inputs
    result = {"action": "unknown", "value": 0, "segments": ["all"], "reasoning": "Parsed from input"}

    # Extract action
    if "increase" in nl_lower and ("service" in nl_lower or "target" in nl_lower):
        result["action"] = "increase_target"
    elif "decrease" in nl_lower or "reduce" in nl_lower or "cut" in nl_lower:
        if "budget" in nl_lower:
            result["action"] = "reduce_budget"
        else:
            result["action"] = "reduce_target"

    # Extract value
    numbers = re.findall(r'(\d+\.?\d*)\s*%', nl_input)
    if numbers:
        val = float(numbers[0])
        if "increase_target" == result["action"]:
            if val > 50:
                result["value"] = round(val - service_target, 1)
            else:
                result["value"] = val
        elif "reduce_target" == result["action"]:
            if val > 50:
                result["value"] = round(val - service_target, 1)
            else:
                result["value"] = val
        elif "reduce_budget" == result["action"]:
            result["value"] = val * 1000000 if val < 100 else val
        elif "increase_budget" == result["action"]:
            result["value"] = val * 1000000 if val < 100 else val

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

        system_prompt = """You are a retail strategy advisor. Write ONLY 2-3 sentences in business language.
Use these terms: service level, safety stock, budget, stockout risk. No thinking, no reasoning."""

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


def frame_decision(decision_context: str, dept_id: int, budget: float, current_service: float) -> Dict[str, Any]:
    """Frame a high-stakes decision. Reject invalid inputs."""
    # First: validate this is a legitimate decision context
    if not client:
        chase_up = budget * 0.02
        chase_down = budget * 0.03
        hold_down = budget * 0.05
        return {
            "options": [
                {"option": "Chase", "description": "Place POs mid-season to meet original targets",
                 "upside": chase_up, "downside": -chase_down, "recommendation": True,
                 "explanation": f"Chase: Increase purchasing mid-season to meet targets despite forecast errors. Upside: +${chase_up/1_000_000:.1f}M sales uplift (~{int(chase_up/budget*100)}% revenue capture), Downside: -${chase_down/1_000_000:.1f}M potential sales loss if demand isn't met. PO volume: ~${chase_up:,.0f} in additional orders."},
                {"option": "Hold", "description": "Accept miss and adjust targets",
                 "upside": 0, "downside": -hold_down, "recommendation": False,
                 "explanation": f"Hold: Accept the mid-season miss and adjust targets. Downside: -${hold_down/1_000_000:.1f}M potential sales loss from unmet demand (~{int(hold_down/budget*100)}% of budget at risk). No additional PO volume."}
            ],
            "recommendation": "Chase"
        }

    system_prompt_validate = """You are a retail decision validator. Determine if the input is a valid mid-season decision context.

VALID contexts are ONLY about:
- Demand changes (underforecasted, overforecasted, demand spike/drop)
- Supply chain issues (vendor delay, transport cost increase, lead time change)
- Inventory issues (running low on stock, excess inventory)
- Cost changes (material cost increase, tariff changes)

INVALID contexts include:
- Non-sensical text ("yo bro", "asdf")
- Unrelated topics (weather, sports, personal questions)
- Vague requests without context

Return ONLY this JSON, nothing else:
{"valid": true} for valid inputs
{"valid": false, "guidance": "..."} for invalid inputs (guidance: 1 sentence on what to describe)"""
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
                guidance = llm_result.get("guidance", "Describe a mid-season issue: demand change, supply delay, inventory problem, or cost increase.")
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
        system_prompt = """YOU ARE A JSON GENERATOR. Output ONLY valid JSON, nothing else.

STRICT RULES:
- Output ONLY this JSON format, no other text:
  {"options": [{"option": "...", "description": "...", "upside": float, "downside": float, "explanation": "..."}], "recommendation": "..."}
- NO thinking, NO reasoning, NO parenthetical notes
- NO text before or after the JSON
- NO phrases like "Wait", "Let me", "Here's", "Based on"
- Keep explanations to 1 sentence, plain English
- Generate 2-3 decision options SPECIFIC to the context provided (e.g., "Expedite shipping", "Negotiate with vendor", "Adjust safety stock")
- For upside/downside: explain these are net financial impact in dollars
- DO NOT always use "Chase" and "Hold" - use context-appropriate option names"""
        user_prompt = f"""Context: {decision_context}
State: Dept {dept_id}, Budget ${budget:,.0f}, Service {current_service}%

Respond JSON ONLY:"""

        content = _call_llm(system_prompt, user_prompt)
        if "{" in content:
            json_start = content.index("{")
            json_end = content.rindex("}") + 1
            return json.loads(content[json_start:json_end])
        chase_up = budget * 0.02
        chase_down = budget * 0.03
        hold_down = budget * 0.05
        return {
            "options": [
                {"option": "Chase", "description": "Place POs mid-season to meet original targets",
                 "upside": chase_up, "downside": -chase_down, "recommendation": True,
                 "explanation": f"Chase: Increase purchasing mid-season to meet targets despite forecast errors. Upside: +${chase_up:,.0f} net gain, Downside: -${chase_down:,.0f} net loss."},
                {"option": "Hold", "description": "Accept miss and adjust targets",
                 "upside": 0, "downside": -hold_down, "recommendation": False,
                 "explanation": f"Hold: Accept the mid-season miss and adjust targets. Downside: -${hold_down:,.0f} net loss from lost sales."}
            ],
            "recommendation": "Chase"
        }
    except Exception:
        chase_up = budget * 0.02
        chase_down = budget * 0.03
        hold_down = budget * 0.05
        return {
            "options": [
                {"option": "Chase", "description": "Place POs mid-season to meet original targets",
                 "upside": chase_up, "downside": -chase_down, "recommendation": True,
                 "explanation": f"Chase: Increase purchasing mid-season to meet targets despite forecast errors. Upside: +${chase_up:,.0f} net gain, Downside: -${chase_down:,.0f} net loss."},
                {"option": "Hold", "description": "Accept miss and adjust targets",
                 "upside": 0, "downside": -hold_down, "recommendation": False,
                 "explanation": f"Hold: Accept the mid-season miss and adjust targets. Downside: -${hold_down:,.0f} net loss from lost sales."}
            ],
            "recommendation": "Chase"
        }
