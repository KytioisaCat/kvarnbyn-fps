# Material och vegetation — Gamla torget-provet

Källorna är Poly Havens CC0-bibliotek, hämtade via dess offentliga API 2026-10-29.
`../assets-src/manifest.json` innehåller exakta källsidor, upphovspersoner, kartfiler,
URL:er, storlekar och MD5-kontrollsummor. Filerna kontrolleras av `fetch_assets.py`.

Materialkitet är tio uppsättningar med albedo, roughness och OpenGL-normaler.
Hero-material (panel, tak, asfalt, smågatsten) är 2k; övriga 1k. Totalt för kitet
inklusive löv-/grenatlas: **47,29 MB**. Inga 8k-kartor, höjdkartor eller kompletta
miljonpolygon-träd har laddats ned.

- **Panel:** fotografiskt normal-/roughness-underlag. Albedot är omålat brunt trä;
  för vit panel ska färgen sättas från husreferensen och underlaget användas för
  småskalig relief. Panelens stående riktning bestäms av geometrin och UV:erna.
- **Puts:** vit grov puts, småskalig normalstyrka.
- **Tegel/tak:** rött väggtegel och ett separat set med tegelpannor.
- **Mark:** asfalt, smågatsten, gräs/jord och granitblock för sockel/stödmur.
- **Bark:** Willow Bark. Generiska trädtillgångar kan använda den utan påstående om
  att ett visst träd i Kvarnbyn är en pil.

`blender_materials.py` gör exporterbara Principled-material utan procedurala
shaderkedjor som går förlorade vid glTF-export. UV:er uttrycks som repetitioner;
`tile_size_m` i manifestet ger fysisk skala. Normalmapparna är OpenGL (+Y).

## Vegetationens ärliga begränsning

Poly Havens fulla lövträdskandidater hade ungefär 1,8–4,7 miljoner polygoner och
kostade 46–101 MB med endast 1k-kartor. De har därför **inte** hämtats som modeller.
Löv-/grenatlasen från `tree_small_02` används som fotografiskt ytunderlag för nya,
lätta grenade träd. Källans angivna art är **Burkea africana**; löven är en generell
visuell proxy, inte korrekt artbestämning eller bevis på svensk vegetation.
Trädposition, höjd och kronform måste väljas från platsreferenser separat.

## Licens

Poly Haven anger samtliga tillgångar som **CC0-1.0**, med rätt till bearbetning och
redistribution: https://polyhaven.com/license

Hämtning sker via det rekommenderade API:t med identifierande User-Agent:
https://polyhaven.com/llms.txt . Manifestet är källförteckningen; inga preview-renderar
från Poly Havens webbplats ingår som produktmaterial.

## Trädkitet och verifiering

`../assets-src/vegetation/vegetation.blend` innehåller de appendbara samlingarna
`Broadleaf_A`, `Broadleaf_B` och `Broadleaf_C`. Varje träd har **6 102 trianglar**, två
meshar/material och en gemensam uppsättning fotograferad bark/lövatlas. Höjdvarianter:
7,8 m, 6,5 m och 8,6 m. De är unga/glesa generiska lövträd, inte mogna, artkorrekta
rekonstruktioner av torgets träd. Ingen krona är byggd av sfärer.

`blender_vegetation.place_tree(...)` placerar varianter med delade meshdata i en
annan Blender-scen. Samtliga källsamlingar har origo vid markens mitt; Blender Z upp.
Individuella `.glb`-filer (ca 4,44 MB/st, med samma inbäddade källtexturer) finns som
alternativ för import i spelmotorn, men världsexporten bör dela texturerna.

Kontrollerat 2026-10-29:

- Två Cycles-renderingar med visuell iteration av krona, skottvinklar och bladnormaler.
  Slutlig granskningsbild: `../assets-src/vegetation/trees_preview.png`.
- GLB-strukturen har `alphaMode: MASK`, tröskel 0,45 och dubbelsidiga löv. Det undviker
  transparent blandning/sortering av hela kronan. Ett svagt, exporterbart emissivt
  bidrag (0,10) approximerar tunna blads ljusgenomsläpp.
- Normalerna för lövkorten är riktade utåt/uppåt för jämnare ljus över kronan.
- Alla nedladdade tillgångar har verifierad MD5 mot källans API.

Bygg om med Blender 4.5 LTS:

```
v2/.tools/Blender.app/Contents/MacOS/Blender -b --python v2/poc/torget/assets-src/build_vegetation.py
```

På denna Mac måste native Blender-körningen få normal macOS-grafikåtkomst; första
körningen i den begränsade processen kraschade före skriptstart. Kör inte samma
begränsade start igen. Den efterföljande körningen med rätt åtkomst skapade och
renderade samtliga tillgångar utan skriptfel.

## Mobil GLB utan geometriförändring

`../assets-src/optimize_glb.py` begränsar inbäddade bilder till 1 024 px och kodar
om färg-, normal- och ORM-kartor till JPEG kvalitet 88. Vektornormaler och separata
ORM-kanaler använder 4:4:4 för att undvika kromasubsampling mellan datakanaler.
Löv med alpha behåller PNG och sin alpha-mask. Skriptet gör inga nätverksanrop och
kräver endast Pillow (finns redan i `tools/venv`).

Första hela världsexporten minskade **73,59 → 29,56 MB (−59,83 %)**; bilddatan
minskade **54,00 → 9,97 MB**. Samtliga 577 icke-bild-bufferViews är byteidentiska,
27 bilder/23 material/32 texturreferenser finns kvar och alla nod-, mesh-, accessor-
och materialfält är exakt bevarade. BufferViews packas med fyra bytes justering.
Världens deklarerade gränser var identiska före och efter optimeringen.

Bildförlusten mäts mot den nedskalade källan. Lägsta färgkanal-PSNR var 30,12 dB
(asfaltens normal), och normalernas genomsnittliga riktning ändrades ungefär
1,4–4,8 grader för de omkodade kartorna; 95-percentilen var som mest 9,7 grader.
Det är en redovisad kvalitetsavvägning för mobilstorlek, inte en förlustfri export.
`--quality 92` kan användas för en större variant. Lövens befintliga 1k-PNG är
oförändrad. Detaljer finns i `mobile-glb-qa.json`.

```
tools/venv/bin/python v2/poc/torget/assets-src/optimize_glb.py \
  --input world.raw.glb --output world.glb --report mobile-glb-qa.json
```

Första provet skrevs till `/private/tmp/torget_mobile.glb`; den då aktiva
`godot/assets/world.glb` ändrades inte av materialagenten.

## Naturligt berg till branta ytor

`natural_rock` i huvudmanifestet är **Rock 01** av Rob Tuytel, Poly Haven CC0.
Setet är naturligt, väderbitet grått fast berg och saknar murverk/fogar. Albedo,
OpenGL-normal och roughness i 1k upptar tillsammans **1 870 599 bytes**. Fysisk
repetition: **1,5 × 1,5 m**. Bilderna är visuellt granskade; inga bruna tegel-/
murmaterial har använts som ersättning för berg. Geologin är en generell visuell
proxy, inte uppmätt Kvarnbyberg. Separat källmanifest finns i
`../assets-src/materials/natural_rock/manifest.json`.
