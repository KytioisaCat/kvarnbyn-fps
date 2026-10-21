#!/bin/bash
# Setup-script för Claude Code cloud-miljön "kvarnbyn" (körs som root före varje session,
# måste bli klart på ~5 min för att cachas). Nätverk: Full.
#
# I miljöns "Setup script"-fält räcker EN rad (undviker klistringsfel med flerradig text):
#   curl -fsSL https://raw.githubusercontent.com/KytioisaCat/kvarnbyn-fps/main/.claude/cloud-setup.sh | bash
#
# Allt är tolerant: ett misslyckat delsteg får aldrig stoppa sessionen (exit 0 alltid).
set -u

log() { echo "[cloud-setup] $*"; }

# Repo-rot om repot redan är klonat (annars körs repo-stegen i sessionen i stället)
REPO=""
for d in "${CLAUDE_PROJECT_DIR:-}" "$PWD" /workspace/* /home/*/* /root/*; do
  if [ -n "$d" ] && [ -f "$d/v2/package.json" ]; then REPO="$d"; break; fi
done

# 1) Headless Chromium för smoke-tester (mjukvaru-WebGL via SwiftShader — ingen GPU i VM:en)
if npx --yes playwright@1.56.0 install --with-deps chromium >/dev/null 2>&1; then
  log "playwright chromium ok"
else
  log "VARNING: playwright-install misslyckades (smoke-tester av)"
fi

# 2) Python-pipelinen (tools/). rasterio behövs bara för fetch_* mot Lantmäteriet — hoppas över.
pip install --break-system-packages --quiet numpy pillow shapely >/dev/null 2>&1 \
  || pip3 install --quiet numpy pillow shapely >/dev/null 2>&1 \
  || log "VARNING: pip-install misslyckades"

# 3) Repo-beroende steg
if [ -n "$REPO" ]; then
  log "repo: $REPO"
  if (cd "$REPO/v2" && { [ -f package-lock.json ] && npm ci --no-audit --no-fund || npm install --no-audit --no-fund; } >/dev/null 2>&1); then
    log "npm install ok"
  else
    log "VARNING: npm install misslyckades — kör 'cd v2 && npm install' i sessionen"
  fi
  if [ -f "$REPO/tools/lidar_1m.png" ] && [ ! -f "$REPO/tools/lidar_full.npy" ]; then
    python3 "$REPO/tools/lidar_png.py" unpack >/dev/null 2>&1 && log "lidar_full.npy återskapad" || log "VARNING: lidar unpack misslyckades"
  fi
else
  log "repot inte klonat ännu — npm install/lidar unpack görs i sessionen"
fi

log "klart"
exit 0
