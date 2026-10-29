#!/bin/zsh
# Bygger om hela provkvarteret från skript: Blender → optimerad GLB → Godot-import (UV2) →
# ljusbake (Vulkan, öppnar editorfönstret ~1 min) → webbexport för telefon.
# Kör från repots rot:   v2/poc/torget/rebuild.sh            (allt)
#                        v2/poc/torget/rebuild.sh --no-blender   (hoppa över Blender-steget)
#                        v2/poc/torget/rebuild.sh --no-bake      (behåll befintlig ljuskarta)
# Kräver verktygen i v2/.tools/ (se BRIEF.md) och tools/venv (Pillow).
set -e
ROOT=${0:A:h:h:h:h}
cd "$ROOT"
P=v2/poc/torget
G=v2/.tools/Godot.app/Contents/MacOS/Godot
B=v2/.tools/Blender.app/Contents/MacOS/Blender
LOG=$P/runtime-docs
step() { print -P "%B==> $1%b" }

if [[ " $* " != *" --no-blender "* ]]; then
  step "Blender: bygger scenen och exporterar blender/world_raw.glb"
  $B -b --python $P/scripts/build_scene.py -- > $LOG/blender-build.log 2>&1
  grep SCENE_METRICS $LOG/blender-build.log | cut -c1-160
fi

step "Optimerar GLB (1k-texturer) → godot/assets/world.glb"
tools/venv/bin/python $P/assets-src/optimize_glb.py --input $P/blender/world_raw.glb \
  --output $P/godot/assets/world.glb --report $P/asset-docs/mobile-glb-qa.json --max-size 1024 > /dev/null
rm -f $P/godot/assets/world_*.jpg $P/godot/assets/world_*.png $P/godot/assets/world_*.import $P/godot/assets/world.glb.unwrap_cache

step "Godot: import, importinställningar (UV2 0,5 m, 2× hjältehus), import igen, bakscen"
$G --headless --path $P/godot --editor --import --quit > $LOG/godot-import.log 2>&1
$G --headless --path $P/godot --script res://scripts/configure_import.gd 2>&1 | grep KVARNBYN
$G --headless --path $P/godot --editor --import --quit >> $LOG/godot-import.log 2>&1
if grep -q "SCRIPT ERROR" $LOG/godot-import.log; then grep "SCRIPT ERROR" $LOG/godot-import.log | sort | uniq -c; exit 2; fi
$G --headless --path $P/godot --script res://scripts/prepare_bake.gd 2>&1 | grep KVARNBYN
$G --headless --path $P/godot --script res://scripts/inspect_world.gd 2>&1 | grep -o '"missing_uv2":\[[^]]*\]\|"static_meshes":[0-9]*'

if [[ " $* " != *" --no-bake "* ]]; then
  step "Godot: bakar ljuskartor (grafisk editor, Vulkan — Metal hänger sig)"
  $G --path $P/godot --editor --rendering-method forward_plus --rendering-driver vulkan -- --bake-kvarnbyn > $LOG/godot-bake.log 2>&1
  cat $P/godot/assets/bake_report.json
fi

step "Webbexport för telefon (ETC2/ASTC) → web-mobil/"
rm -rf $P/web-mobil && mkdir -p $P/web-mobil
$G --headless --path $P/godot --export-release "Webb mobil" ../web-mobil/index.html > $LOG/web-export.log 2>&1
ls -la $P/web-mobil/index.pck $P/web-mobil/index.wasm | awk '{printf "  %-40s %6.1f MB\n", $9, $5/1e6}'
step "Klart. Servera med:  python3 -m http.server 8790 --directory $P/web-mobil"
