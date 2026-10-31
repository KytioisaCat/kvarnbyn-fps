# Försvara Kvarnbyn — aktiv datorversion

Blender bygger världen och modellerna, Godot 4.7.2 kör spelet med Forward+ och realtidsljus.
`../poc/torget/` är fryst material-/kitreferens. Äldre Three.js-kod är historik.

## Spela lokalt

Efter återbyggnad finns den uppackade Mac-appen här:

```sh
open "v2/kvarnbyn/desktop/app/Försvara Kvarnbyn.app"
```

WASD · mus · vänsterklick skjut · högerklick sikta · R ladda om · Shift spring · C huka ·
mellanslag hoppa/raketdubbelhopp · F flygtest · Esc paus.

## Bygg om

Från repots rot: `v2/kvarnbyn/rebuild.sh`. Kräver projektets lokala Blender/Godot-verktyg
under `v2/.tools/`, Godots macOS-mall och Pythonmiljön `tools/venv/`. Kedjan tolkar data,
bygger mark/värld, bygger Ak 5/soldat, optimerar GLB, importerar, kör kontrollprov och
exporterar/packar upp Mac-appen. `--no-export` hoppar över appen; `--bot` kör även en hel botomgång.
Loggar finns i `evidence/`. Misslyckade bygge-/kontrollsteg avbryter kedjan.

**Agenternas tester är alltid tysta:** `--audio-driver Dummy`; testskript och automatiska
capture/bot/probe/walktest mutar dessutom masterbussen. Stäng inte andra Godot-processer.
Vanlig manuell spelstart har ljud.

Genererade GLB/.blend/exporter är lokala och gitignorerade. Soldatens lilla oförändrade
CC0-källa ligger i `assets-src/soldier/`, med licens och hash. Material/träd återanvänds
från det befintliga torget-provet.

## Resultat och nästa steg

- [Senaste platsprovet: Roten M 29](RESULTAT-ROTEN.md)
- [Soldater, vapen och torgförgården](RESULTAT-SOLDATER.md)
- [Fas B: spelregler och grundkänsla](RESULTAT-FAS-B.md)
- [Fas A: hela världen](RESULTAT.md)
- [Vapenmodell och verifiering](blender/AK5.md)
- [Soldatkälla och återbyggnad](assets-src/soldier/README.md)
- [Referenser och begränsningar för Roten M](reference/roten-m/OBSERVATIONER.md)

Läs alltid de tre senaste posterna i projektets `DAGBOK.md` före nästa pass.
