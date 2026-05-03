# Foxtrot Free Deployment Guide

Zero-cost setup for hosting Foxtrot on Streamlit Cloud with Supabase.

## Architecture

```
Streamlit Cloud (free)
    ├── streamlit_app.py (frontend agent's work)
    ├── backend/ (optimizer, LLM, database client)
    └── supabase/ (schema already created)

Supabase (free tier)
    ├── scenarios table (user what-if scenarios)
    ├── optimization_cache table (7-day TTL)
    └── decisions table (high-stakes decisions)
```

## Quick Start (15 min setup)

### 1. Supabase (5 min)

1. Sign up at https://supabase.com (free)
2. Create new project (name: "foxtrot", password: save it!)
3. Go to **SQL Editor** → New Query
4. Copy contents of `supabase/schema.sql` → Run
5. Go to **Project Settings** → **API**
6. Copy:
   - `URL`: `https://xxxxx.supabase.co`
   - `anon/public` key: `eyJhbG...`

### 2. GitHub (2 min)

```bash
git init
git add .
git commit -m "Initial commit"
gh repo create foxtrot --public
git push -u origin main
```

### 3. Streamlit Cloud (5 min)

1. Sign up at https://streamlit.io/cloud (free, link GitHub)
2. Click **"New app"**
3. Fill in:
   - **Repository**: yourusername/foxtrot
   - **Branch**: main
   - **Main file path**: `streamlit_app.py` (frontend agent will create this)
   - **Requirements file**: `requirements.txt`
4. Click **"Advanced settings"** → **"Secrets"**:
   ```toml
   SUPABASE_URL = "https://xxxxx.supabase.co"
   SUPABASE_ANON_KEY = "eyJ..."
   ANTHROPIC_API_KEY = "sk-ant-..."
   ```
5. Click **"Deploy"**

### 4. Verify

- App URL: `https://your-app.streamlit.app`
- Test: Set budget=$100M, service=97%, dept=101
- Check Supabase → Table Editor → `scenarios` table for saved data

## Free Tier Limits

| Service | Limit | Workaround |
|---|---|---|
| Streamlit Cloud | 3 apps, public repo | Use org account for more |
| Streamlit RAM | 1GB RAM | Optimizer runs in-process |
| Supabase DB | 500MB | ~50K scenarios |
| Supabase Sleep | 7 days inactive | Click to wake (30s) |
| Supabase API | 50K requests/month | Plenty for prototype |

## Fallback: All-In-Streamlit Mode

If separate backend is too complex, everything runs in Streamlit:

```python
# In streamlit_app.py
import sys
sys.path.append('backend')

# Run optimizer directly (no API calls)
from backend.streamlit_helper import optimize
result = optimize(budget, service_target, dept_id)
```

This uses NO external APIs except:
- Supabase (scenario storage)
- Anthropic (LLM features, optional)

## Files Created for This Setup

| File | Purpose |
|---|---|
| `supabase/schema.sql` | Database schema (run in Supabase) |
| `backend/database.py` | Supabase client (new, safe to use) |
| `backend/streamlit_helper.py` | Streamlit-frontend helper (new) |
| `backend/__init__.py` | Package init (new) |
| `requirements.txt` | Streamlit Cloud requirements (new) |
| `backend/requirements.txt` | Updated with `supabase` |
| `.streamlit/secrets.toml.example` | Secrets template (new) |
| `.env.example` | Local dev env template (new) |
| `data/*.json` | Sample data for optimizer (new) |
| `deploy/streamlit-cloud.md` | Detailed deployment guide (new) |

## Cost Summary

| Component | Cost |
|---|---|
| Streamlit Cloud | $0 |
| Supabase | $0 |
| GitHub | $0 |
| Anthropic API | ~$5/mo (usage-based, optional) |
| **Total** | **$0** (or $5 with LLM) |
