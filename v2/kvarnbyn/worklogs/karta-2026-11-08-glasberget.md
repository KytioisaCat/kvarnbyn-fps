# Karta — Glasberget, klippor och höjdskillnader

**Status:** kartspårets första pass klart, överlämnat till integration. **Startcommit:** 9f3674d. **Gren:** codex/karta/glasberget.
**Arbetskopia:** /private/tmp/kvarnbyn-karta-glasberget.

Joel beskriver Glasberget som huvudsakligen klippor med skog/gröna partier ovanpå.
Mål: synlig bergkaraktär, läsbara höjdskillnader och stödjande murar där underlag
finns. Börja med platslokalisering, LiDAR/OSM och faktiska bildreferenser; skilj
belagda egenskaper från uppskattningar. Inga spel-/balansändringar.

Reserverat i kartspåret: terrängdelen av blender/build_world.py och nya isolerade
berg-/markhjälpare; pipeline/site.py endast om terrängmetadata behöver utökas.
Gemensamma world/overlay/byggfiler samordnas först vid integration.
Kartans materialimport, ny terrängshader och egna capture-/verifieringsskript
ingår också. Ingen annan skrivare arbetar i dem. Integratören ska koppla det
nya artefaktprovet till rebuild.sh.

Prov ska vara ljudlösa. Stora lokala tillgångar kopieras, inte delade skrivbara
symlänkar; agenten skriver inte i main från kartspåret. Central status uppdateras
av integratören när den färdiga ändringen förs ihop.

## Genomfört

- Rå LiDAR-lutning och klasskarta styr kontinuerlig bergexponering. Mjuka,
  uppskattade områdesmasker för Lilla Glasberget, större Glasberget och dess
  framsida sedd från övre Görjelycksgatan. Joels senare förtydligande flyttade
  huvudprovet till spawn[340,153] mot bergsidan[490,250].
- Vertexvikter exporteras uttryckligen som GLB COLOR_0. Godot blandar befintliga
  CC0-berg-/grästexturer och skogsmark; världsprojektion på tre axlar ger berg
  utan utdragning på branta sidor. Två texturskalor gör berg mer läsbart på håll.
- Två befintliga OSM-murlinjer byggda som låga stenmurar med riktig kollision.
  Planläge belagt i OSM, höjd/bredd uppskattade, inga nya höga terrasskärningar.
  Ingen av linjerna skär befintliga vägbuffertar. Se referensloggen för källor
  och vad bilderna faktiskt visar respektive skymmer.
- Nya svenska granskningsvyer tillagda sist i menylistan; gamla index och spawn
  bevarade. Inget nytt runtimeformat krävs av spelspåret.

## Utförda prov

- Alla8472befintliga GLB-meshars expanderade triangelpositioner och transform
  identiska mot accepterad värld. Bara två murmesh + två kollisionsmesh tillagda.
- Båda höjdfälten och alla övriga site.json-fält identiska. Vatten/gator/träd,
  skyddade gångytor, spelbalans, nav och kartunderlag bevarade.
-309048terrängvertexvikter i levererad GLB;46258mellanvikter. Optimeraren
  bevarar alla icke-bildbuffertar byteidentiskt.
- Importerad värld:7prov gröna, inklusive272/272tvåsidiga strålar mot murarna.
  Strålarna isolerar murkropparna eftersom deras övre sida avsiktligt är jordtäckt.
-180/180gångpunkter över hela zonen, Stallelidens riktiga kapsel-/räckesprov
  och27gripkroksprov gröna. Alla agentkörningar ljudlösa.
- Fem jämförbara före/eftervyer plus två nya huvudvyer mot berget från starten.
  Alla sju slutvyer granskade i native Forward+. Första materialprovet godkänt
  tekniskt; klippfasadens finform och verklig igenkänning återstår att arbeta vidare
  med. Integration/app-export återstår vid denna överlämning.

## Lokalt paket och kvarstående

GLB SHA256:8f705acdb00405f19008935de432ad0ed81aa78c88e9ab3cb9718e26a3061f6c.
Egen arbetskopia har site.json, world.glb, world_meta.json och byggloggar.
Råloggar/bilder/artefaktprov: `v2/.tools/kvarnbyn-rock-20261108/`.
Stora genererade tillgångar ska inte checkas in.

Detta är ett första material-/nivåläsbarhetspass, inte en inmätt modell av varje
klippstup. Exakta stup/sprickor, vegetationens avsatser, murarnas grindöppningar
och villornas riktiga utseende återstår. Uppskattningar får inte märkas som
platsgranskad färdiggeometri. Ingen datahämtning eller ny textur nedladdad.
