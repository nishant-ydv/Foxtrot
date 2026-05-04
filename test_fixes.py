"""Test script to validate all 50 test cases for Foxtrot bugs."""
import sys
import os

# Add backend to path
sys.path.insert(0, "E:/Foxtrot/backend")

from llm_layer import parse_scenario, _fallback_decision

# Test data
BUDGET = 100_000_000  # $100M
SERVICE = 97.0
DEPT_ID = 101
CURRENT_POLICY = {"configs": {"A": {"dcc_pct": 97.0}, "B": {"dcc_pct": 95.0}}}

print("=" * 60)
print("SCENARIO EXPLORER TESTS (25 cases)")
print("=" * 60)

scenario_tests = [
    # (input, expected_action, expected_min_val, expected_max_val)
    ("what if budget is $50M", "reduce_budget", 50_000_000, 50_000_000),
    ("increase budget by $10M", "increase_budget", 10_000_000, 10_000_000),
    ("decrease budget by $5M", "reduce_budget", 5_000_000, 5_000_000),
    ("service 99%", "increase_target", 2.0, 2.0),  # 99 - 97 = 2
    ("reduce service to 90%", "reduce_target", 7.0, 7.0),  # 97 - 90 = 7
    ("demand is 2x", "demand_change", 2.0, 2.0),
    ("demand doubled", "demand_change", 2.0, 2.0),
    ("lead time increases by 2 weeks", "unknown", 0, 0),  # Not handled yet
    ("what if budget drops $3M", "reduce_budget", 3_000_000, 3_000_000),
    ("budget 120", "increase_budget", 20_000_000, 20_000_000),  # 120 - 100 = 20M
    ("cut budget in half", "reduce_budget", 50_000_000, 50_000_000),  # 50% of 100M
    ("increase target to 98%", "increase_target", 1.0, 1.0),
    ("decrease target by 5%", "reduce_target", 5.0, 5.0),
    ("service level 85%", "reduce_target", 12.0, 12.0),  # 97 - 85 = 12
    ("budget $200M", "increase_budget", 100_000_000, 100_000_000),
    ("demand drops by 30%", "demand_change", 0.7, 0.7),  # 1 - 0.3 = 0.7
    ("demand spikes 50%", "demand_change", 1.5, 1.5),  # 1 + 0.5 = 1.5
    ("vendor delay", "invalid", 0, 0),  # Supply chain
    ("asdf", "invalid", 0, 0),
    ("yo bro", "invalid", 0, 0),
    ("double the service target", "increase_target", 0, 100),  # Vague
    ("budget $0", "reduce_budget", 100_000_000, 100_000_000),  # Edge case
    ("service 50%", "reduce_target", 47.0, 47.0),
    ("increase budget 500%", "increase_budget", 500_000_000, 500_000_000),  # 500% of 100M = 500M
    ("", "unknown", 0, 0),
]

passed = 0
failed = 0

for i, (nl_input, expected_action, min_val, max_val) in enumerate(scenario_tests, 1):
    result = parse_scenario(nl_input, CURRENT_POLICY, BUDGET, SERVICE)
    action = result.get("action", "unknown")
    value = result.get("value", 0)
    error = result.get("error", False)

    # Determine if test passed
    passed_test = False
    if expected_action == "invalid":
        passed_test = (action == "invalid" or error)
    else:
        passed_test = (action == expected_action) and (min_val <= value <= max_val or min_val == value)

    status = "PASS" if passed_test else "FAIL"
    if passed_test:
        passed += 1
    else:
        failed += 1

    print(f"[{status}] Test {i:2d}: '{nl_input[:40]}'")
    if not passed_test:
        print(f"       Expected: action={expected_action}, value={min_val}-{max_val}")
        print(f"       Got: action={action}, value={value}, error={error}")

print()
print("=" * 60)
print("HIGH-STAKES DECISION TESTS (25 cases)")
print("=" * 60)

decision_tests = [
    # (context, expected_recommendation)
    ("underforecasted by 20%", "Chase"),
    ("overforecasted by 20%", "Hold"),
    ("forecast low", "Chase"),  # underforecast (forecast is low)
    ("forecast high", "Hold"),  # overforecast
    ("demand spike", "Chase"),
    ("demand drop", "Hold"),
    ("vendor delay", "Negotiate"),  # or Expedite
    ("transport cost doubled", "Negotiate"),
    ("running low on stock", "Chase"),
    ("excess inventory", "Hold"),
    ("material cost increase", "Negotiate"),
    ("tariff changes", "Negotiate"),
    ("underforecast holiday by 20% for Product X", "Chase"),
    ("overforecasted holiday by 20%", "Hold"),
    ("supply chain disruption", "Negotiate"),
    ("lead time increased 3 weeks", "Expedite"),
    ("shortage in key SKUs", "Chase"),
    ("too much inventory", "Hold"),
    ("stockout risk high", "Chase"),
    ("asdf", "Invalid"),
    ("yo bro", "Invalid"),
    ("weather is nice", "Invalid"),
    ("demand is 2x expected", "Chase"),
    ("demand half of forecast", "Hold"),
    ("", "Invalid"),
]

passed2 = 0
failed2 = 0

for i, (context, expected_rec) in enumerate(decision_tests, 1):
    result = _fallback_decision(context, BUDGET)  # Use fallback to test keywords
    recommendation = result.get("recommendation", "Unknown")

    # Handle "Invalid" expected
    if expected_rec == "Invalid":
        passed_test = ("Invalid" in recommendation or "invalid" in recommendation)
    else:
        passed_test = (expected_rec.lower() in recommendation.lower())

    status = "PASS" if passed_test else "FAIL"
    if passed_test:
        passed2 += 1
    else:
        failed2 += 1

    print(f"[{status}] Test {i:2d}: '{context[:40]}'")
    if not passed_test:
        print(f"       Expected: {expected_rec}")
        print(f"       Got: {recommendation}")

print()
print("=" * 60)
print(f"RESULTS: Scenario Tests: {passed}/{passed+failed} passed, {failed} failed")
print(f"         Decision Tests: {passed2}/{passed2+failed2} passed, {failed2} failed")
print("=" * 60)
