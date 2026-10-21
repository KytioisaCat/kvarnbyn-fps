#!/bin/bash
# Setup-script för Claude Code cloud-miljön "kvarnbyn".
# Klistra in innehållet i miljöns "Setup script" på claude.ai/code (körs som root före varje
# session, måste bli klart på ~5 min för att cachas). Nätverk: Full (CC0-texturer från
# Poly Haven/ambientCG, OSM m.m. ligger utanför standardlistan).
set -euo pipefail

# Repo-rot: Claude Code klonar till arbetskatalogen; hitta den oavsett namn.
ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$ROOT"

# 1) v2 (Vite/TypeScript/Three.js)
if [ -f v2/package.json ]; then
  (cd v2 && if [ -f package-lock.json ]; then npm ci --no-audit --no-fund; else npm install --no-audit --no-fund; fi)
fi

# 2) Headless Chromium för smoke-tester (mjukvaru-WebGL via SwiftShader — ingen GPU i VM:en).
#    Playwright hamnar i ~/.cache/ms-playwright; --with-deps drar systembibliotek via apt.
npx --yes playwright@1.56.0 install --with-deps chromium >/dev/null 2>&1 || echo "VARNING: playwright-install misslyckades (smoke-tester av)"

# 3) Python-pipelinen (tools/). rasterio behövs bara för fetch_* mot Lantmäteriet — hoppas över.
pip install --break-system-packages --quiet numpy pillow shapely 2>/dev/null || pip3 install --quiet numpy pillow shapely

# 4) Återskapa LiDAR-griden ur den committade 16-bit-PNG:n (gitignorerad .npy)
if [ -f tools/lidar_1m.png ] && [ ! -f tools/lidar_full.npy ]; then
  python3 tools/lidar_png.py unpack
fi

echo "cloud-setup klart: node $(node -v), python $(python3 --version)"
