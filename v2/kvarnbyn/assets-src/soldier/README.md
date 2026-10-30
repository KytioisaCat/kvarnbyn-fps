# Soldatkälla

`Swat.gltf` är den oförändrade källfilen från **Quaternius, Ultimate Modular Men Pack**,
hämtad 2026-10-30. Filen är 3 368 868 byte och innehåller 24 namngivna animationer.
Skaparens medföljande `LICENSE.txt` anger CC0 1.0. Källa, direktlänk och SHA-256 finns i
`manifest.json`. Källan versionshanteras för att återbyggnad inte ska bero på Drive-kvoten.

Bygg vapnet först, sedan soldaten (från repots rot):

```sh
v2/.tools/Blender.app/Contents/MacOS/Blender -b --python-exit-code 1 --python v2/kvarnbyn/blender/build_ak5.py
v2/.tools/Blender.app/Contents/MacOS/Blender -b --python-exit-code 1 --python v2/kvarnbyn/blender/build_soldier.py
```

Det ger `godot/assets/characters/soldier.glb` (lokalt, gitignorerat), en gemensam skinnad mesh
med 62 ben och 24 klipp. Källans pistol/custom bone shape tas bort. Överkroppen i gång/löpning
bakas om med tvåbens-IK till gevärsfattning; vår Ak 5 monteras på bröstbenet. Det är ett stiliserat
standardinfanteri, ingen uppmätt modell av ett svenskt förband. Geväret är kortat till 78 % för
modellens proportioner. Materialen får två delade lagvarianter i Godot.

`godot/scripts/soldier_visual.gd` äger animationsvalet och korrigerar axelkonventionen för
Blenders benmonterade vapen vid import. `CharacterBody3D` äger all förflyttning; klippen är
på plats och ger inga världspositionshopp. Huvudträffzonen följer det animerade huvudbenet.

Snabb verifiering efter Godot-import:

```sh
v2/.tools/Godot.app/Contents/MacOS/Godot --audio-driver Dummy --headless --path v2/kvarnbyn/godot --script res://scripts/verify_soldier_visual.gd
```

Provet kontrollerar namngivna klipp, huvudhöjd, mynningsläge framåt och att dödsanimationen
inte loopar. Nativebild kan tas med samma kommando utan `--headless` och
`-- --capture=/absolut/sökväg.png`. Modellmätningar finns i `evidence/soldier-model.json`.
