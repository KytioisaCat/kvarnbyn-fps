# Gamla torget — första innehålls- och motorprovet

Start: 2026-10-29. Joel har godkänt cirka fyra till fem timmars autonomt arbete,
subagenter samt rimliga relevanta nedladdningar och installationer. Detta ersätter
kravet på separat godkännande för varje nedladdning under detta pass. Inga köp.

## Frågan

Kan ett litet utsnitt av Kvarnbyn byggas med riktig innehållsproduktion i Blender,
och behålla sin karaktär när samma modeller visas i ett spelbart webbprov?

## Omfattning

- Arbetsruta cirka 120 × 120 meter vid Gamla torget, WGS84 57.65690, 12.02780.
- Kråkans krog som huvudbyggnad, omkringliggande hus i fallande detaljnivå.
- Terräng från befintlig LiDAR, gator/torg, fors/strand, vegetation och gatuföremål.
- Återanvändbara byggnadsdelar/material i Blender, glTF-export och Godot Compatibility.
- Gå och titta med mus/tangentbord eller touch; förvalda jämförelsevyer.
- Källor, säkra fakta och antaganden dokumenteras. Egna/CC0/CC BY-tillgångar i produkten.

## Färdigdefinition

En granskad Blender-scen med bilder från ögonhöjd, samma innehåll i ett verifierat
webbbygge om tekniken håller, samt RESULTAT.md som skiljer mätningar från Joels
kvarstående visuella bedömning. Tester, storlekar, verktygsversioner och återbyggnad
ska gå att följa. Vi lovar ingen automatisk överföring av hela Cycles-utseendet.

## Avgränsning

Ingen ny strids-AI, inga vapen eller fullskalig stadsgenerering. v1 är referens och
ändras inte. Den tidigare Three.js-renderaren byggs inte vidare som produkt.
Terrain3D är ett separat möjligt prov, inte ett basberoende. Stor Unity/Unreal-
installation görs bara om ett konkret hinder motiverar den.

## Lagring och nedladdningar

Lokala verktyg ligger gitignorerade under v2/.tools/. Blender 4.5 LTS för Apple
Silicon (~308 MB), Godot 4.7.2 standard (~171 MB), endast behövliga exportmallar
(webb cirka 20 MB, macOS cirka 123 MB). Material/vegetation har inledningsvis en
budget på 250 MB. Exakta mottagna storlekar dokumenteras i resultatet.
