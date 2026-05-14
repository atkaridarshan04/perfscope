#!/usr/bin/env bash
# setup.sh — one-time setup for running WITHOUT Docker (local dev)
set -e

echo "==> Installing system tools..."
sudo apt-get update -qq || true   # ignore GPG warnings from third-party repos

# perf is shipped as linux-tools-<kernel> or linux-tools-generic
KERNEL=$(uname -r)
PERF_PKG=""
if apt-cache show "linux-tools-${KERNEL}" &>/dev/null; then
  PERF_PKG="linux-tools-${KERNEL} linux-tools-generic"
elif apt-cache show "linux-perf" &>/dev/null; then
  PERF_PKG="linux-perf"
else
  echo "   [warn] Could not find a perf package — skipping (perf may already be installed)"
fi

sudo apt-get install -y $PERF_PKG sysbench fio stress-ng perl git

echo "==> Cloning FlameGraph scripts..."
if [ ! -d /opt/FlameGraph ]; then
  sudo git clone --depth=1 https://github.com/brendangregg/FlameGraph /opt/FlameGraph
fi

echo "==> Granting perf sudo access (NOPASSWD)..."
PERF_PATH=$(which perf 2>/dev/null || echo "/usr/bin/perf")
SUDOERS_LINE="$USER ALL=(ALL) NOPASSWD: $PERF_PATH"
if ! sudo grep -qF "$SUDOERS_LINE" /etc/sudoers; then
  echo "$SUDOERS_LINE" | sudo tee -a /etc/sudoers > /dev/null
  echo "   Added sudoers entry."
else
  echo "   Sudoers entry already exists."
fi

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Setting up Python backend..."
cd "$REPO_ROOT/backend"
python3 -m venv .venv
source .venv/bin/activate
pip install -q -r requirements.txt

echo "==> Setting up frontend..."
cd "$REPO_ROOT/frontend"
npm install

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start:"
echo "  Backend:  cd backend && source .venv/bin/activate && uvicorn app.main:app --reload"
echo "  Frontend: cd frontend && npm run dev"
