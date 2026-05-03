"""LLM Layer — Anthropic Claude integration for Foxtrot.

Handles:
- Natural language → parameter changes (intent parsing)
- Trade-off narration (business-language explanations)
- Decision framing (high-stakes decisions)
- Budget feasibility explanations
"""
import os
import json
from typing import Dict, Any, List, Optional
from anthropic import Anthropic


# Initialize Claude client
api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
client = Anthropic(api_key=api_key) if api_key else None

MODEL = "claude-sonnet-4-6"  # Cost-effective for V0


def parse_scenario(nl_input: str, current_policy: Dict[str, Any], budget: float, service_target: float) -> Dict[str, Any]:
    """Parse natural language scenario into optimizer parameter changes.

    Args:
        nl_input: Natural language scenario, e.g. "What if budget drops $3M?"
        current_policy: Current policy configs per segment.
        budget: Current budget.
        service_target: Current service target.

    Returns:
        Dict with 'action', 'changes', and 'updated_budget' or 'updated_target'.
    """
    system_prompt = """You are an inventory policy assistant for retail Category Business Owners.
Parse the user's natural language scenario into structured parameter changes.

Available actions:
- reduce_budget: Decrease budget by specified amount
- increase_budget: Increase budget by specified amount
- reduce_target: Lower service level target by specified percentage points
- increase_target: Raise service level target
- cut_safety_stock: Reduce safety stock on specified segments
- cut_dcc: Reduce DCC/service level on specified segments

Respond in JSON format with: action, value (dollar amount or percentage), segments (list, or "all"), and reasoning."""

    user_prompt = f"""Current state:
- Budget: ${budget:,.0f}
- Service target: {service_target}%
- Policy configs: {json.dumps(current_policy, indent=2)}

User scenario: "{nl_input}"

Respond with JSON only: {{"action": "<action>", "value": <number>, "segments": ["<segment>"], "reasoning": "<why>"}}"""

    if not client:
        return {
            "action": "unknown",
            "value": 0,
            "segments": [],
            "reasoning": "LLM unavailable: ANTHROPIC_API_KEY not set",
            "error": True
        }

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=500,
            messages=[{"role": "user", "content": user_prompt}],
            system=system_prompt
        )
        content = response.content[0].text.strip()

        # Extract JSON from response
        if "{" in content:
            json_start = content.index("{")
            json_end = content.rindex("}") + 1
            result = json.loads(content[json_start:json_end])
        else:
            result = {"action": "unknown", "value": 0, "segments": [], "reasoning": "Could not parse"}

        return result
    except Exception as e:
        return {
            "action": "error",
            "value": 0,
            "segments": [],
            "reasoning": f"LLM parsing failed: {str(e)}",
            "error": True
        }


def narrate_tradeoff(
    old_policy: Dict[str, Any],
    new_policy: Dict[str, Any],
    budget_change: float,
    service_change: float
) -> str:
    """Generate business-language narration of trade-offs between two policies.

    Args:
        old_policy: Previous policy configs per segment.
        new_policy: New policy configs per segment.
        budget_change: Change in budget ($).
        service_change: Change in service level (percentage points).

    Returns:
        Business-language narration string.
    """
    system_prompt = """You are a retail inventory strategy advisor. Write a concise, business-focused
narration (2-3 sentences) explaining the trade-offs between two inventory policy configurations.

Focus on:
- What changed and why
- The business impact (service level vs. cost)
- Risk assessment (stockout risk, capital tied up)
- Concrete numbers (percentages, dollar amounts)

Use the CBO's language: "service level", "safety stock", "budget", "stockout risk"."""

    changes = []
    if old_policy and new_policy:
        for seg in new_policy.get("configs", {}):
            if seg in old_policy.get("configs", {}):
                old_cfg = old_policy["configs"][seg]
                new_cfg = new_policy["configs"][seg]
                dcc_change = new_cfg.get("dcc_pct", 0) - old_cfg.get("dcc_pct", 0)
                if abs(dcc_change) > 0.1:
                    changes.append(f"{seg}: DCC {dcc_change:+.1f}%")

    user_prompt = f"""Policy comparison:
- Budget change: ${budget_change:+,.0f}
- Service level change: {service_change:+.1f} percentage points
- Segment changes: {', '.join(changes) if changes else 'Minor adjustments'}

Write a 2-3 sentence narration in business language that explains:
1. What was changed and why
2. The trade-off (cost vs. service)
3. The risk (stockout risk, capital impact)"""

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=300,
            messages=[{"role": "user", "content": user_prompt}],
            system=system_prompt
        )
        return response.content[0].text.strip()
    except Exception as e:
        # Fallback narration
        if budget_change < 0:
            return (f"Reducing budget by ${-budget_change:,.0f} saves costs but "
                    f"{'reduces' if service_change < 0 else 'maintains'} service level "
                    f"by {abs(service_change):.1f} percentage points. "
                    f"Review segment configs for stockout risk.")
        else:
            return (f"Budget increase of ${budget_change:,.0f} allows "
                    f"{'improved' if service_change > 0 else 'maintained'} service level "
                    f"({service_change:+.1f} pts). Capital tied up increases accordingly.")


def explain_infeasibility(budget: float, service_target: float, min_budget: float) -> str:
    """Explain why budget is insufficient and what options exist.

    Args:
        budget: The requested budget.
        service_target: The requested service level target.
        min_budget: The minimum budget required.

    Returns:
        Business-language explanation with 3 actionable options.
    """
    gap = min_budget - budget
    gap_pct = (gap / budget) * 100

    system_prompt = """You are a retail inventory strategy advisor. Explain budget infeasibility
in business language. Be specific about dollar amounts and service level impacts.

Always provide 3 clear options:
1. Increase budget to the minimum required
2. Keep current budget but accept lower service level
3. Lower the target service level to fit current budget"""

    user_prompt = f"""Budget analysis:
- Requested budget: ${budget:,.0f}
- Target service level: {service_target}%
- Minimum budget required: ${min_budget:,.0f}
- Budget gap: ${gap:,.0f} ({gap_pct:.1f}%)

Also calculate: What service level CAN be achieved with ${budget:,.0f}?
(Use rough estimate: if budget is X% of minimum, service is roughly X% of target, with minimum 80%.)

Provide a concise explanation (2-3 sentences) and clearly list the 3 options."""

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=400,
            messages=[{"role": "user", "content": user_prompt}],
            system=system_prompt
        )
        return response.content[0].text.strip()
    except Exception as e:
        # Fallback explanation
        achievable = max(80.0, service_target * (budget / min_budget))
        return (
            f"⚠️ Budget Insufficient\n\n"
            f"Target: {service_target}% WIP with ${budget:,.0f} is not achievable.\n"
            f"Minimum budget required: ${min_budget:,.0f} (${gap:,.0f} more).\n\n"
            f"With ${budget:,.0f}, you can achieve approximately {achievable:.1f}% WIP.\n\n"
            f"Your options:\n"
            f"1. Increase budget to ${min_budget:,.0f} → achieve {service_target}% WIP\n"
            f"2. Keep ${budget:,.0f} → achieve {achievable:.1f}% WIP (see configs below)\n"
            f"3. Lower target to {achievable:.0f}% → achieve with ${budget:,.0f}"
        )


def frame_decision(decision_context: str, dept_id: int, budget: float, current_service: float) -> Dict[str, Any]:
    """Frame a high-stakes decision with ranked options and quantified trade-offs.

    Args:
        decision_context: Description of the decision, e.g. "Underforecasted holiday by 20%"
        dept_id: Department ID.
        budget: Current budget.
        current_service: Current service level.

    Returns:
        Dict with 'options' (list of options with upside/downside) and 'recommendation'.
    """
    system_prompt = """You are a retail strategy advisor. Frame high-stakes inventory decisions
for Category Business Owners.

For each option provide:
- Option name
- Description
- Upside ($, %, or business impact)
- Downside ($, %, or business impact)
- Recommendation (true/false)

Always provide 2-3 options. Be quantitative where possible."""

    user_prompt = f"""Decision context: {decision_context}

Current state:
- Department: {dept_id}
- Budget: ${budget:,.0f}
- Current service level: {current_service}%

Frame this as a decision with 2-3 options. Respond in JSON:
{{
  "options": [
    {{"option": "Chase", "description": "...", "upside": 2500000, "downside": -1800000, "recommendation": true}},
    {{"option": "Hold", "description": "...", "upside": 0, "downside": -500000, "recommendation": false}}
  ],
  "recommendation": "Chase"
}}"""

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=600,
            messages=[{"role": "user", "content": user_prompt}],
            system=system_prompt
        )
        content = response.content[0].text.strip()

        if "{" in content:
            json_start = content.index("{")
            json_end = content.rindex("}") + 1
            result = json.loads(content[json_start:json_end])
        else:
            result = {"options": [], "recommendation": "Unknown"}

        return result
    except Exception as e:
        # Fallback decision framing
        return {
            "options": [
                {
                    "option": "Chase demand",
                    "description": "Place additional POs to meet the forecast surge",
                    "upside": budget * 0.02,  # 2% revenue upside
                    "downside": -budget * 0.03,  # 3% cost if wrong
                    "recommendation": True
                },
                {
                    "option": "Hold course",
                    "description": "Accept the miss, avoid additional inventory risk",
                    "upside": 0,
                    "downside": -budget * 0.05,  # 5% lost sales
                    "recommendation": False
                }
            ],
            "recommendation": "Chase demand",
            "note": f"LLM unavailable: {str(e)}"
        }
