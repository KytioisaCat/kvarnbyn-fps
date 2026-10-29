# Dagbok — överlämning mellan agenter

Joel låter flera AI-agenter (Claude Code, ChatGPT Codex, …) jobba i repot omväxlande, ofta
tills tokens tar slut mitt i ett pass. Den här filen är hur ni lämnar över till varandra.

## Regler (gäller alla agenter)

1. **Läs de tre senaste inläggen först**, innan TODO.md och allt annat. De säger var förra
   agenten slutade, vad som är halvfärdigt och vad som är trasigt.
2. **Skriv ett inlägg när du börjar** (en rad räcker: vem, när, vad du tänker göra) — så syns
   det om du dör mitt i passet.
3. **Skriv klart inlägget innan du tar slut**, helst vid varje delsteg. Om du märker att tokens
   tar slut: skriv dagboken FÖRE nästa tunga kommando. Ett ofullständigt inlägg är bättre än inget.
4. **Nyaste inlägget överst.** Format nedan. Kort och konkret: filer, kommandon, siffror.
5. **Committa ofta** med dagboken i samma commit. Okommittat arbete kan inte nästa agent lita på.
6. `CLAUDE.md` är projektinstruktionerna. `AGENTS.md` är en exakt kopia för Codex:
   ändrar du den ena, kör `cp CLAUDE.md AGENTS.md`.
7. Stora genererade filer (GLB, EXR, .blend, webb-/macOS-export) committas inte — de byggs om
   med kommandona i respektive README. Skriv i dagboken om något bara finns lokalt.

## Inläggsformat

```
## ÅÅÅÅ-MM-DD HH:MM — <agent/modell> — <rubrik>
**Status:** pågår | klart | avbrutet (varför)
**Gjort:** punktlista med filer/kommandon/siffror
**Läge nu:** vad som fungerar, vad som är halvfärdigt, vad som bara finns lokalt
**Nästa:** numrerad lista, första punkten = det nästa agent ska göra först
**Varningar:** fällor, saker som inte får göras, beslut som väntar på Joel
```

---

## 2026-10-29 19:30 — Claude Code (Opus 5.5) — tar över efter Codex, slutför motorprovet

**Status:** pågår

**Gjort hittills:** kartlagt Codex pass (inlägget nedan), skapat denna dagbok, synkat
AGENTS.md med CLAUDE.md.

**Plan för passet:** (1) optimera nya `blender/world_raw.glb` → `godot/assets/world.glb`,
(2) importera + UV2 + baka om med 0,5 m texel och 2× på hjältehusen (Vulkan),
(3) webbexport och mät `.pck`-storleken, (4) jämförelsebilder Godot mot Blender från samma vy,
(5) `RESULTAT.md`, (6) gitignore för stora binärer, committa källor och dokumentation.

---

## 2026-10-29 ~14:00–18:15 — ChatGPT Codex — PoC "Gamla torget" i Blender + Godot (rekonstruerat)

*Skrivet i efterhand av Claude utifrån filer, tidsstämplar och Codex egna README/CHECKPOINT.
Codex tog slut på tokens ~18:15 utan att committa eller skriva överlämning.*

**Status:** avbrutet (tokens slut)

**Gjort:**
- 14:09 commit `8ac5ab9`: lägesgenomgång, kontrollprov i TODO.md, `v2/PLAN.md` märkt historik.
- Verktyg lokalt i `v2/.tools/` (gitignorerat, 1,7 GB): Blender 4.5 LTS, Godot 4.7.2 + webb- och
  macOS-exportmallar.
- `v2/poc/torget/` (inget committat): `BRIEF.md`, platsunderlag `reference/OBSERVATIONER.md`
  (Street View-granskning av Kråkan, Musikskolan, Corpus m.fl., inga pixlar i produkten),
  `data/city_spec.json` (12 hus, 29 vägar, 120×120 m kring 57.65690 N 12.02780 E),
  `scripts/build_scene.py` + `modelkit.py` (Blender: hus ur kit med fasadrytm per hus,
  fönster, markiser, skyltar, tak), CC0-material från Poly Haven (`assets-src/`, 47 MB,
  MD5 i manifest), egna lätta lövträd (6 102 tri/st), finish-material och fönsterinteriörer.
- Godot-projekt `godot/`: FPS-kontroller (dator + touch, 1,65 m ögonhöjd, kliver kantsten
  23 cm, verifierad headless), ljusbake med LightmapGI (252 modeller, 0,25 m texel, Vulkan —
  Metal hänger sig), himmel (HDRI), webbexport (WebGL 2/Compatibility) och macOS-app.
- Punktmolnsprovet: rätt ruta identifierad (`dsm-skoglig-copc`, 91 MB) men råfilen kräver
  inloggning (HTTP 401) och `LM_USER`/`LM_PASS` var osatta → 0 byte hämtat.

**Läge när den slutade:**
- 18:09 byggdes Blender-scenen om med finish-material + fönsterinteriörer →
  `blender/world_raw.glb` (83 MB) och nya bilder i `evidence/`.
- **Godot kör fortfarande den äldre `godot/assets/world.glb` (17:41)** och ljuset är bakat på den
  (17:42). Den nya modellen är alltså inte importerad, optimerad eller bakad.
- Webbexporten (`runtime-docs/smoke-web/index.pck`) är **165 MB** — för stor för telefon.
  En mobiloptimerad GLB (1k-texturer, 30 MB) provades till `/private/tmp/` men användes inte.
- 18:14 hämtades bergmaterialet `rock_01` till manifestet men används inte i `build_scene.py` än.

**Nästa (Codex egen lista ur `runtime-docs/CHECKPOINT.json`):**
1. Importera slutlig optimerad world.glb
2. Verifiera vegetations- och kollisionsundantag för UV2
3. Baka om med 0,5 m globalt och 2× hjältetäthet, dynamiska träd, probes
4. Exportera och verifiera minskad ljuskarts-/PCK-storlek
5. Slutbilder och faktiskt telefonprov med Joel

**Varningar:** baka med `--rendering-driver vulkan` (Metal hänger sig). Lantmäteriets
punktmoln kräver att Joel själv sätter `LM_USER`/`LM_PASS` — be aldrig om lösenord i chatten.
