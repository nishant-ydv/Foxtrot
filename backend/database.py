"""Supabase client for Foxtrot.

Handles:
- Scenario storage and retrieval
- Optimization result caching
- Decision logging
- Session-based access for anonymous users (no auth required for V0)
"""

import os
import json
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from supabase import create_client, Client


def get_supabase_client() -> Optional[Client]:
    """Create and return a Supabase client.

    Returns None if credentials are not set (graceful degradation).
    """
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_ANON_KEY", "").strip()

    if not url or not key:
        return None

    try:
        return create_client(url, key)
    except Exception:
        return None


# ============================================
# SCENARIOS
# ============================================

def save_scenario(
    session_id: str,
    dept_id: int,
    dept_name: str,
    budget: float,
    service_target: float,
    season: str,
    feasible: bool,
    achieved_service: Optional[float],
    total_cost: Optional[float],
    minimum_budget: Optional[float],
    configs: Optional[Dict],
    narration: Optional[str],
    nl_input: Optional[str] = None,
    tags: Optional[List[str]] = None,
    user_id: Optional[str] = None,
) -> Optional[str]:
    """Save a scenario to Supabase.

    Returns the scenario ID if successful, None if Supabase is unavailable.
    """
    supabase = get_supabase_client()
    if not supabase:
        return None

    try:
        data = {
            "session_id": session_id,
            "dept_id": dept_id,
            "dept_name": dept_name,
            "budget": budget,
            "service_target": service_target,
            "season": season,
            "feasible": feasible,
            "achieved_service": achieved_service,
            "total_cost": total_cost,
            "minimum_budget": minimum_budget,
            "configs": configs,
            "narration": narration,
            "nl_input": nl_input,
            "tags": tags or [],
            "user_id": user_id,
        }

        result = supabase.table("scenarios").insert(data).execute()
        if result.data:
            return result.data[0]["id"]
        return None
    except Exception:
        return None


def get_session_scenarios(session_id: str, limit: int = 50) -> List[Dict]:
    """Retrieve scenario history for a session."""
    supabase = get_supabase_client()
    if not supabase:
        return []

    try:
        result = (
            supabase.table("scenarios")
            .select("id, dept_name, budget, service_target, feasible, achieved_service, created_at, tags")
            .eq("session_id", session_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
    except Exception:
        return []


def get_scenario(scenario_id: str) -> Optional[Dict]:
    """Get a single scenario by ID."""
    supabase = get_supabase_client()
    if not supabase:
        return None

    try:
        result = supabase.table("scenarios").select("*").eq("id", scenario_id).execute()
        if result.data:
            return result.data[0]
        return None
    except Exception:
        return None


# ============================================
# OPTIMIZATION CACHE
# ============================================

def _make_cache_key(budget: float, service_target: float, dept_id: int, season: str) -> str:
    """Generate a deterministic cache key."""
    raw = f"{budget:.2f}_{service_target:.2f}_{dept_id}_{season}"
    return hashlib.md5(raw.encode()).hexdigest()


def get_cached_optimization(
    budget: float, service_target: float, dept_id: int, season: str
) -> Optional[Dict]:
    """Retrieve cached optimization result."""
    supabase = get_supabase_client()
    if not supabase:
        return None

    try:
        cache_key = _make_cache_key(budget, service_target, dept_id, season)
        result = (
            supabase.table("optimization_cache")
            .select("result, expires_at")
            .eq("cache_key", cache_key)
            .single()
            .execute()
        )
        if result.data:
            # Check expiry
            expires_at = datetime.fromisoformat(result.data["expires_at"].replace("Z", "+00:00"))
            if expires_at > datetime.now(expires_at.tzinfo):
                return result.data["result"]
        return None
    except Exception:
        return None


def cache_optimization(
    budget: float,
    service_target: float,
    dept_id: int,
    season: str,
    result: Dict,
    ttl_days: int = 7,
) -> None:
    """Cache an optimization result."""
    supabase = get_supabase_client()
    if not supabase:
        return

    try:
        cache_key = _make_cache_key(budget, service_target, dept_id, season)
        data = {
            "cache_key": cache_key,
            "budget": budget,
            "service_target": service_target,
            "dept_id": dept_id,
            "season": season,
            "result": result,
            "expires_at": (datetime.now() + timedelta(days=ttl_days)).isoformat(),
        }

        # Upsert (update if exists, insert if not)
        supabase.table("optimization_cache").upsert(data, on_conflict="cache_key").execute()
    except Exception:
        pass  # Fail silently - cache miss is acceptable


# ============================================
# DECISIONS
# ============================================

def save_decision(
    session_id: str,
    dept_id: int,
    context: str,
    budget: float,
    current_service: float,
    options: List[Dict],
    recommendation: str,
    user_id: Optional[str] = None,
) -> Optional[str]:
    """Log a high-stakes decision."""
    supabase = get_supabase_client()
    if not supabase:
        return None

    try:
        data = {
            "session_id": session_id,
            "dept_id": dept_id,
            "context": context,
            "budget": budget,
            "current_service": current_service,
            "options": options,
            "recommendation": recommendation,
            "user_id": user_id,
        }

        result = supabase.table("decisions").insert(data).execute()
        if result.data:
            return result.data[0]["id"]
        return None
    except Exception:
        return None


# ============================================
# SESSION HELPERS
# ============================================

def generate_session_id() -> str:
    """Generate a random session ID for anonymous users."""
    import uuid
    return str(uuid.uuid4())


def get_or_create_session() -> str:
    """Get existing session from Streamlit, or create a new one."""
    try:
        import streamlit as st
        if "session_id" not in st.session_state:
            st.session_state.session_id = generate_session_id()
        return st.session_state.session_id
    except Exception:
        return generate_session_id()
