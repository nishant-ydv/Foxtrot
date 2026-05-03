# Deploying Foxtrot to Streamlit Cloud (Free)

## Prerequisites

1. **GitHub repo** - Push your code to GitHub (public repo required for free tier)
2. **Supabase account** - Sign up at https://supabase.com (free tier)
3. **Streamlit Cloud account** - Sign up at https://streamlit.io/cloud (free)

## Step 1: Set up Supabase

1. Create a new Supabase project
2. Go to SQL Editor and run the schema from `supabase/schema.sql`
3. Go to Project Settings → API
4. Copy the:
   - Project URL (e.g., `https://abcdefg.supabase.co`)
   - Anon/Public key (starts with `eyJ...`)

## Step 2: Deploy to Streamlit Cloud

1. Go to https://streamlit.io/cloud
2. Click "New app"
3. Connect your GitHub repo
4. Configure:
   - **Repository**: your-foxtrot-repo
   - **Branch**: main (or master)
   - **Main file path**: `streamlit_app.py` (or whatever the frontend agent creates)
   - **Requirements file**: `requirements.txt`

5. Click "Advanced settings" and add secrets:

```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_ANON_KEY = "eyJ..."
ANTHROPIC_API_KEY = "sk-ant-..."
```

6. Click "Deploy"

## Step 3: Verify

- App will be available at: `https://your-app-name.streamlit.app`
- Free tier limits:
  - Public repo required
  - 1GB RAM / ~2 vCPU
  - App sleeps after 15 min inactivity (30s cold start)
  - 3 apps max per account

## Fallback: In-Process Mode

If Streamlit Cloud sleeps cause issues, the app can run the optimizer directly (no separate backend):

```python
# In your Streamlit app
try:
    import backend.optimizer as opt
    # Run optimization in-process
    result = opt.optimize_policy(budget, service_target, dept_id, season)
except ImportError:
    # Fallback to API call
    import requests
    response = requests.post(f"{BACKEND_URL}/optimize", json={...})
```

## Monitoring

- Streamlit Cloud: View logs in the app dashboard
- Supabase: View scenario data in Table Editor
