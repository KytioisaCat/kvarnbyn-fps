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
step "Karta: eget kartunderlag ur hus, mark och höjddata"
$PY $P/pipeline/map_image.py > $LOG/map-build.log
step "Fors: eget flödesfält ur befintlig vattenprofil"
$PY $P/pipeline/river_flow.py > $LOG/river-flow-build.log
step "Blender: bygger världen → blender/world_raw.glb"
$B -b --python-exit-code 1 --python $P/blender/build_world.py > $LOG/blender-build.log 2>&1
grep SCENE_METRICS $LOG/blender-build.log | cut -c1-200
step "Optimerar texturer (2k) → godot/assets/world.glb"
$PY v2/poc/torget/assets-src/optimize_glb.py --input $P/blender/world_raw.glb --output $P/godot/assets/world.glb \
  --report $LOG/glb-qa.json --max-size 2048 --quality 88 > /dev/null
ls -la $P/godot/assets/world.glb | awk '{printf "  world.glb %.1f MB\n", $5/1e6}'
step "Kontroll: exporterade gångtrianglar och växternas markkontakt"
$PY $P/reference/stalliden/qa-export.py --glb $P/blender/world_raw.glb --site $P/data/site.json --out $LOG/stalliden-mesh-after.json > $LOG/stalliden-mesh-check.log
step "Kontroll: M25:s exporterade entré och ursprungliga L-kontur"
$PY $P/reference/stalliden/qa-export.py --area m25 --glb $P/blender/world_raw.glb --site $P/data/site.json --out $LOG/m25-mesh-check.json > $LOG/m25-mesh-check.log
step "Kontroll: norra åbankens exporterade gångytor"
$PY $P/reference/stalliden/qa-export.py --area north_bank --glb $P/blender/world_raw.glb --site $P/data/site.json --out $LOG/north-bank-mesh-check.json > $LOG/north-bank-mesh-check.log
step "Blender: Ak 5 och riggade soldater"
$B -b --python-exit-code 1 --python $P/blender/build_ak5.py > $LOG/weapon-build.log 2>&1
$B -b --python-exit-code 1 --python $P/blender/build_soldier.py > $LOG/soldier-build.log 2>&1
$B -b --python-exit-code 1 --python $P/blender/build_civilians.py > $LOG/civilian-build.log 2>&1
step "Godot: import (två varv: importinställningar emellan)"
$G --audio-driver Dummy --headless --path $P/godot --editor --import --quit > $LOG/godot-import-1.log 2>&1
$G --audio-driver Dummy --headless --path $P/godot --script res://scripts/configure_import.gd 2>&1 | grep KVARNBYN
$G --audio-driver Dummy --headless --path $P/godot --editor --import --quit > $LOG/godot-import-2.log 2>&1
if grep -qE "SCRIPT ERROR|ERROR:" $LOG/godot-import-1.log $LOG/godot-import-2.log; then grep -E "SCRIPT ERROR|ERROR:" $LOG/godot-import-1.log $LOG/godot-import-2.log | sort | uniq -c; exit 2; fi
awk '/KVARNBYN_TREES/ { last=$0 } END { if (last != "") print last }' $LOG/godot-import-1.log $LOG/godot-import-2.log
step "Kontroll: berg/grönska, texturer och kartlagda murkollisioner"
$G --audio-driver Dummy --headless --path $P/godot --script res://scripts/verify_terrain.gd > $LOG/terrain-check.log 2> $LOG/terrain-check.stderr.log
$PY -c 'import json,sys; r=json.loads(next(x.split("KVARNBYN_TERRAIN_CHECK ",1)[1] for x in open(sys.argv[1]) if x.startswith("KVARNBYN_TERRAIN_CHECK "))); assert r["passed"]' $LOG/terrain-check.log
step "Kontroll: kontroller och gångprov"
$G --audio-driver Dummy --headless --fixed-fps 60 --path $P/godot --script res://scripts/verify_controller.gd 2>&1 | grep -E "KVARNBYN|PASS|FAIL" | tail -3
step "Kontroll: gripkrokens sving, fartbygge, släpp och kollision"
$G --audio-driver Dummy --headless --fixed-fps 60 --path $P/godot --script res://scripts/verify_grapple.gd > $LOG/grapple-check.log 2> $LOG/grapple-check.stderr.log
$PY -c 'import json,sys; r=json.loads(next(x.split("KVARNBYN_GRAPPLE_CHECK ",1)[1] for x in open(sys.argv[1]) if x.startswith("KVARNBYN_GRAPPLE_CHECK "))); assert r["passed"]' $LOG/grapple-check.log
step "Kontroll: rörelsemeny, sparning och verklig effekt av reglagen"
$G --audio-driver Dummy --headless --fixed-fps 60 --path $P/godot --script res://scripts/verify_movement.gd -- --no-pointer-lock --no-movement-profile > $LOG/movement-check.log 2> $LOG/movement-check.stderr.log
$PY -c 'import json,sys; r=json.loads(next(x.split("KVARNBYN_MOVEMENT_CHECK ",1)[1] for x in open(sys.argv[1]) if x.startswith("KVARNBYN_MOVEMENT_CHECK "))); assert r["passed"] and len(r["checks"])>=25' $LOG/movement-check.log
step "Kontroll: gångytor över hela världen"
$G --audio-driver Dummy --headless --fixed-fps 60 --path $P/godot -- --explore --walktest > $LOG/walk-check.log 2>&1
step "Kontroll: Roten M 29, gård och grind"
$G --audio-driver Dummy --headless --fixed-fps 60 --path $P/godot --script res://scripts/verify_roten.gd -- --explore --no-pointer-lock --output="$ROOT/$LOG/roten-ground-check.json" > $LOG/roten-ground-check.log 2>&1
step "Kontroll: hela Stalleliden upp och ned samt räcke"
$G --audio-driver Dummy --headless --fixed-fps 60 --path $P/godot --script res://scripts/verify_roten.gd -- --explore --no-pointer-lock --check-key=stalliden_ground_checks --report-prefix=KVARNBYN_STALLIDEN_CHECK --output="$ROOT/$LOG/stalliden-ground-check.json" > $LOG/stalliden-ground-check.log 2>&1
step "Kontroll: M25 från vilplan till dörr och tillbaka"
$G --audio-driver Dummy --headless --fixed-fps 60 --path $P/godot --script res://scripts/verify_roten.gd -- --explore --no-pointer-lock --check-key=m25_ground_checks --report-prefix=KVARNBYN_M25_CHECK --output="$ROOT/$LOG/m25-ground-check.json" > $LOG/m25-ground-check.log 2>&1
step "Kontroll: norra åbankens gång/cykelstråk i båda riktningar"
$G --audio-driver Dummy --headless --fixed-fps 60 --path $P/godot --script res://scripts/verify_roten.gd -- --explore --no-pointer-lock --check-key=north_bank_ground_checks --report-prefix=KVARNBYN_NORTH_BANK_CHECK --output="$ROOT/$LOG/north-bank-ground-check.json" > $LOG/north-bank-ground-check.log 2>&1
step "Kontroll: kartans underlag och orientering"
$G --audio-driver Dummy --headless --path $P/godot --script res://scripts/verify_map.gd -- --output="$ROOT/$LOG/map-check.json" > $LOG/map-check.log 2>&1
step "Kontroll: kartknappar och paus i riktig spelvärld"
$G --audio-driver Dummy --headless --fixed-fps 60 --path $P/godot --script res://scripts/verify_map_world.gd -- --no-pointer-lock --output="$ROOT/$LOG/map-world-check.json" > $LOG/map-world-check.log 2>&1
step "Kontroll: frontläge, förstärkningshåll och baslarm på kartan"
rm -f $LOG/front-check.json
$G --audio-driver Dummy --headless --fixed-fps 60 --path $P/godot --script res://scripts/verify_front.gd -- --no-pointer-lock --output="$ROOT/$LOG/front-check.json" > $LOG/front-check.log 2>&1
$PY -c 'import json,sys; r=json.load(open(sys.argv[1])); assert r["passed"] and len(r["checks"])>=27' $LOG/front-check.json
step "Kontroll: botens zonmål och rensningspatrull"
rm -f $LOG/patrol-check.json
$G --audio-driver Dummy --headless --fixed-fps 60 --path $P/godot --script res://scripts/verify_bot_patrol.gd -- --no-pointer-lock --output="$ROOT/$LOG/patrol-check.json" > $LOG/patrol-check.log 2>&1
$PY -c 'import json,sys; r=json.load(open(sys.argv[1])); assert r["passed"] and len(r["checks"])>=16' $LOG/patrol-check.json
step "Kontroll: allierades basvakter ersätts efter förluster"
rm -f $LOG/allied-roles-check.json
$G --audio-driver Dummy --headless --fixed-fps 60 --path $P/godot --script res://scripts/verify_allied_roles.gd -- --no-pointer-lock --output="$ROOT/$LOG/allied-roles-check.json" > $LOG/allied-roles-check.log 2>&1
$PY -c 'import json,sys; r=json.load(open(sys.argv[1])); assert r["passed"] and len(r["checks"])>=19' $LOG/allied-roles-check.json
step "Kontroll: målvisning och baslarm i riktig spelvärld"
$G --audio-driver Dummy --headless --fixed-fps 60 --path $P/godot --script res://scripts/verify_objective.gd -- --no-pointer-lock --output="$ROOT/$LOG/objective-check.json" > $LOG/objective-check.log 2>&1
step "Kontroll: forsens riktningar och faktiska vattenmaterial"
$G --audio-driver Dummy --headless --fixed-fps 60 --path $P/godot --script res://scripts/verify_water.gd -- --explore --no-pointer-lock --output="$ROOT/$LOG/water-check.json" > $LOG/water-check.log 2>&1
step "Kontroll: trädplaceringar efter import"
$G --audio-driver Dummy --headless --fixed-fps 60 --path $P/godot --script res://scripts/verify_trees.gd -- --explore > $LOG/tree-check.log 2>&1
step "Kontroll: kvällsljus, gatlyktor och menybyte"
$G --audio-driver Dummy --headless --fixed-fps 60 --path $P/godot --script res://scripts/verify_lighting.gd -- --explore --no-pointer-lock --output="$ROOT/$LOG/lighting-check.json" > $LOG/lighting-check.log 2>&1
step "Kontroll: fyra civila, kroppstyper, samtal och skydd från strid"
$G --audio-driver Dummy --headless --fixed-fps 60 --path $P/godot --script res://scripts/verify_civilians.gd -- --no-pointer-lock --no-movement-profile > $LOG/civilian-check.log 2> $LOG/civilian-check.stderr.log
$PY -c 'import json,sys; r=json.load(open(sys.argv[1])); assert r["passed"] and len(r["checks"])>=29' $LOG/civilian-check.json
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
  step "Kontroll: civila modeller, samtal och skydd i exporterad Mac-app"
  "$P/desktop/app/Försvara Kvarnbyn.app/Contents/MacOS/Försvara Kvarnbyn" --audio-driver Dummy --headless --fixed-fps 60 -- --no-pointer-lock --no-movement-profile --civilian-export-check > $LOG/civilian-export-check.log 2> $LOG/civilian-export-check.stderr.log
  $PY -c 'import json,sys; r=json.loads(next(x.split("KVARNBYN_CIVILIAN_CHECK ",1)[1] for x in open(sys.argv[1]) if x.startswith("KVARNBYN_CIVILIAN_CHECK "))); assert r["passed"] and r["release"] and len(r["checks"])>=29' $LOG/civilian-export-check.log
  step "Kontroll: bergmaterial och murar finns i exporterad Mac-app"
  "$P/desktop/app/Försvara Kvarnbyn.app/Contents/MacOS/Försvara Kvarnbyn" --audio-driver Dummy --headless -- --explore --no-pointer-lock --terrain-export-check > $LOG/terrain-export-check.log 2> $LOG/terrain-export-check.stderr.log
  $PY -c 'import json,sys; r=json.loads(next(x.split("KVARNBYN_TERRAIN_EXPORT_CHECK ",1)[1] for x in open(sys.argv[1]) if x.startswith("KVARNBYN_TERRAIN_EXPORT_CHECK "))); assert r["passed"] and r["release"]' $LOG/terrain-export-check.log
  step "Kontroll: kartan finns också i exporterad Mac-app"
  "$P/desktop/app/Försvara Kvarnbyn.app/Contents/MacOS/Försvara Kvarnbyn" --audio-driver Dummy --headless -- --explore --no-pointer-lock --map-export-check > $LOG/map-export-check.log 2>&1
  step "Kontroll: frontläget fungerar också i exporterad Mac-app"
  "$P/desktop/app/Försvara Kvarnbyn.app/Contents/MacOS/Försvara Kvarnbyn" --audio-driver Dummy --headless -- --no-pointer-lock --front-export-check > $LOG/front-export-check.log 2>&1
  $PY -c 'import json,sys; lines=open(sys.argv[1]).read().splitlines(); r=json.loads(next(x.split("KVARNBYN_FRONT_EXPORT_CHECK ",1)[1] for x in lines if x.startswith("KVARNBYN_FRONT_EXPORT_CHECK "))); assert r["passed"] and r["release"]' $LOG/front-export-check.log
  step "Kontroll: botpatrull med riktig kapsel i exporterad Mac-app"
  "$P/desktop/app/Försvara Kvarnbyn.app/Contents/MacOS/Försvara Kvarnbyn" --audio-driver Dummy --headless --fixed-fps 60 -- --no-pointer-lock --patrol-export-check > $LOG/patrol-export-check.log 2>&1
  $PY -c 'import json,sys; r=json.loads(next(x.split("KVARNBYN_PATROL_EXPORT_CHECK ",1)[1] for x in open(sys.argv[1]) if x.startswith("KVARNBYN_PATROL_EXPORT_CHECK "))); assert r["passed"] and r["release"]' $LOG/patrol-export-check.log
  step "Kontroll: basvakter ersätts också i exporterad Mac-app"
  "$P/desktop/app/Försvara Kvarnbyn.app/Contents/MacOS/Försvara Kvarnbyn" --audio-driver Dummy --headless -- --no-pointer-lock --guards-export-check > $LOG/guards-export-check.log 2>&1
  $PY -c 'import json,sys; lines=open(sys.argv[1]).read().splitlines(); r=json.loads(next(x.split("KVARNBYN_GUARDS_EXPORT_CHECK ",1)[1] for x in lines if x.startswith("KVARNBYN_GUARDS_EXPORT_CHECK "))); assert r["passed"] and r["release"]' $LOG/guards-export-check.log
  step "Kontroll: flödesfältet finns också i exporterad Mac-app"
  "$P/desktop/app/Försvara Kvarnbyn.app/Contents/MacOS/Försvara Kvarnbyn" --audio-driver Dummy --headless -- --explore --no-pointer-lock --water-export-check > $LOG/water-export-check.log 2>&1
  step "Kontroll: gripkrok, fartbygge och stadskollision i exporterad Mac-app"
  "$P/desktop/app/Försvara Kvarnbyn.app/Contents/MacOS/Försvara Kvarnbyn" --audio-driver Dummy --headless --fixed-fps 60 -- --explore --no-pointer-lock --grapple-export-check > $LOG/grapple-export-check.log 2> $LOG/grapple-export-check.stderr.log
  $PY -c 'import json,sys; r=json.loads(next(x.split("KVARNBYN_GRAPPLE_EXPORT_CHECK ",1)[1] for x in open(sys.argv[1]) if x.startswith("KVARNBYN_GRAPPLE_EXPORT_CHECK "))); assert r["passed"] and r["release"] and r["city"]["passed"]' $LOG/grapple-export-check.log
  step "Kontroll: rörelsereglagen i exporterad Mac-app"
  "$P/desktop/app/Försvara Kvarnbyn.app/Contents/MacOS/Försvara Kvarnbyn" --audio-driver Dummy --headless --fixed-fps 60 -- --no-pointer-lock --movement-export-check > $LOG/movement-export-check.log 2> $LOG/movement-export-check.stderr.log
  $PY -c 'import json,sys; r=json.loads(next(x.split("KVARNBYN_MOVEMENT_CHECK ",1)[1] for x in open(sys.argv[1]) if x.startswith("KVARNBYN_MOVEMENT_CHECK "))); assert r["passed"] and r["release"] and len(r["checks"])>=25' $LOG/movement-export-check.log
fi
step "Klart på $(( $(date +%s) - t0 )) s. Kör:  $G --path $P/godot"
