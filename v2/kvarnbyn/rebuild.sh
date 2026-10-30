#!/bin/zsh
# Bygger om Kvarnbyn (Fas A) från källdata: tolkning → markytor → Blender → GLB → Godot-import
# → macOS-app. Ingen ljusbake (realtids-GI). Kör från repots rot:
#   v2/kvarnbyn/rebuild.sh              allt
#   v2/kvarnbyn/rebuild.sh --no-export  hoppa över macOS-exporten
#   v2/kvarnbyn/rebuild.sh --bot        kör också ett automatiskt spelprov (Fas B)
# Kräver v2/.tools/ (Blender 4.5, Godot 4.7.2 + macOS-exportmall) och tools/venv.
set -e
set -o pipefail
ROOT=${0:A:h:h:h}
cd "$ROOT"
P=v2/kvarnbyn
G=v2/.tools/Godot.app/Contents/MacOS/Godot
B=v2/.tools/Blender.app/Contents/MacOS/Blender
PY=tools/venv/bin/python
LOG=$P/evidence
step() { print -P "%B==> $1%b" }
t0=$(date +%s)

step "Tolkning: data/city.json"
(cd $P/pipeline && ../../../$PY interpret.py)
step "Markytor: data/site.json"
(cd $P/pipeline && ../../../$PY site.py) | tail -3
step "Blender: bygger världen → blender/world_raw.glb"
$B -b --python-exit-code 1 --python $P/blender/build_world.py > $LOG/blender-build.log 2>&1
grep SCENE_METRICS $LOG/blender-build.log | cut -c1-200
step "Optimerar texturer (2k) → godot/assets/world.glb"
$PY v2/poc/torget/assets-src/optimize_glb.py --input $P/blender/world_raw.glb --output $P/godot/assets/world.glb \
  --report $LOG/glb-qa.json --max-size 2048 --quality 88 > /dev/null
ls -la $P/godot/assets/world.glb | awk '{printf "  world.glb %.1f MB\n", $5/1e6}'
step "Blender: Ak 5 och riggade soldater"
$B -b --python-exit-code 1 --python $P/blender/build_ak5.py > $LOG/weapon-build.log 2>&1
$B -b --python-exit-code 1 --python $P/blender/build_soldier.py > $LOG/soldier-build.log 2>&1
step "Godot: import (två varv: importinställningar emellan)"
$G --audio-driver Dummy --headless --path $P/godot --editor --import --quit > $LOG/godot-import-1.log 2>&1
$G --audio-driver Dummy --headless --path $P/godot --script res://scripts/configure_import.gd 2>&1 | grep KVARNBYN
$G --audio-driver Dummy --headless --path $P/godot --editor --import --quit > $LOG/godot-import-2.log 2>&1
if grep -qE "SCRIPT ERROR|ERROR:" $LOG/godot-import-1.log $LOG/godot-import-2.log; then grep -E "SCRIPT ERROR|ERROR:" $LOG/godot-import-1.log $LOG/godot-import-2.log | sort | uniq -c; exit 2; fi
awk '/KVARNBYN_TREES/ { last=$0 } END { if (last != "") print last }' $LOG/godot-import-1.log $LOG/godot-import-2.log
step "Kontroll: kontroller och gångprov"
$G --audio-driver Dummy --headless --fixed-fps 60 --path $P/godot --script res://scripts/verify_controller.gd 2>&1 | grep -E "KVARNBYN|PASS|FAIL" | tail -3
step "Kontroll: gångytor över hela världen"
$G --audio-driver Dummy --headless --fixed-fps 60 --path $P/godot -- --explore --walktest > $LOG/walk-check.log 2>&1
step "Kontroll: trädplaceringar efter import"
$G --audio-driver Dummy --headless --fixed-fps 60 --path $P/godot --script res://scripts/verify_trees.gd -- --explore > $LOG/tree-check.log 2>&1
step "Kontroll: soldatmodell och stridsfysik"
$G --audio-driver Dummy --headless --path $P/godot --script res://scripts/verify_soldier_visual.gd > $LOG/soldier-visual.log 2>&1
$G --audio-driver Dummy --headless --fixed-fps 60 --path $P/godot --script res://scripts/verify_soldiers.gd > $LOG/soldier-tactics.log 2>&1
$G --audio-driver Dummy --headless --fixed-fps 60 --path $P/godot --script res://scripts/verify_weapon.gd > $LOG/weapon-check.log 2>&1
if [[ " $* " == *" --bot "* ]]; then
  step "Spelprov: en hel omgång med bot (4× fart)"
  $G --audio-driver Dummy --headless --path $P/godot -- --bot --speed=4 --botlimit=1500 2>&1 | grep KVARNBYN_BOT | cut -c1-300
fi
if [[ " $* " != *" --no-export "* ]]; then
  step "macOS-app → desktop/Kvarnbyn.zip"
  mkdir -p $P/desktop
  $G --audio-driver Dummy --headless --path $P/godot --export-release "macOS" ../desktop/Kvarnbyn.zip > $LOG/macos-export.log 2>&1
  ls -la $P/desktop/Kvarnbyn.zip | awk '{printf "  Kvarnbyn.zip %.0f MB\n", $5/1e6}'
  mkdir -p $P/desktop/app
  ditto -x -k $P/desktop/Kvarnbyn.zip $P/desktop/app
fi
step "Klart på $(( $(date +%s) - t0 )) s. Kör:  $G --path $P/godot"
