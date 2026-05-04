#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# local-qa-setup.sh
# Run once to install everything the local-qa-agent needs.
# Usage: bash scripts/local-qa/setup.sh
# ─────────────────────────────────────────────────────────────────────────────
set -e

echo "══════════════════════════════════════════"
echo "  Local QA Agent — Environment Setup"
echo "══════════════════════════════════════════"

# ── 1. Python Playwright ───────────────────────────────────────────────────
echo ""
echo "[1/4] Installing Python Playwright..."

# Detect the right pip command
if command -v pip3 &>/dev/null; then
  PIP="pip3"
elif command -v pip &>/dev/null; then
  PIP="pip"
elif command -v python3 &>/dev/null; then
  PIP="python3 -m pip"
elif command -v python &>/dev/null; then
  PIP="python -m pip"
else
  echo "      ✗ No pip or python found. Install Python 3 first."
  exit 1
fi
echo "      Using: $PIP"

$PIP install playwright --break-system-packages -q 2>/dev/null \
  || $PIP install playwright -q
python3 -m playwright install chromium --with-deps
echo "      ✓ Playwright (Python) ready"

# ── 2. Node Playwright (if package.json exists) ───────────────────────────
if [ -f "package.json" ]; then
  echo ""
  echo "[2/4] Installing Node Playwright..."
  npm install -D playwright @playwright/test --silent
  npx playwright install chromium
  echo "      ✓ Playwright (Node) ready"
else
  echo ""
  echo "[2/4] No package.json found — skipping Node Playwright"
fi

# ── 3. Create required directories ────────────────────────────────────────
echo ""
echo "[3/4] Creating QA directories..."
mkdir -p .qa-logs/screenshots
mkdir -p .agent-state
mkdir -p .streamlit
chmod 755 .qa-logs .agent-state
echo "      ✓ Directories created"

# ── 4. Streamlit config (suppress email prompt + headless mode) ────────────
echo ""
echo "[4/4] Writing Streamlit config..."

mkdir -p ~/.streamlit
cat > ~/.streamlit/credentials.toml << 'EOF'
[general]
email = ""
EOF

# Only write .streamlit/config.toml if it doesn't already exist
if [ ! -f ".streamlit/config.toml" ]; then
  cat > .streamlit/config.toml << 'EOF'
[server]
headless = true
port = 8501
enableCORS = false
enableXsrfProtection = false

[browser]
gatherUsageStats = false
EOF
  echo "      ✓ .streamlit/config.toml written"
else
  echo "      ✓ .streamlit/config.toml already exists — not overwritten"
fi

# ── Add .qa-logs to .gitignore ────────────────────────────────────────────
if [ -f ".gitignore" ]; then
  if ! grep -q ".qa-logs" .gitignore; then
    echo "" >> .gitignore
    echo "# Local QA Agent" >> .gitignore
    echo ".qa-logs/" >> .gitignore
    echo "      ✓ Added .qa-logs/ to .gitignore"
  fi
fi

echo ""
echo "══════════════════════════════════════════"
echo "  Setup complete. You can now invoke:"
echo "  @local-qa-agent validate my app"
echo "══════════════════════════════════════════"
