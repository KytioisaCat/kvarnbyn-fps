# Stalliden — gångunderlag ur befintlig export

2026-11-01, baslinje `ca119f9`. Läses tillsammans med `data-review.walk.json`; återkör med `tools/venv/bin/python v2/kvarnbyn/reference/stalliden/data-review.walk.py`.

**Detta är geometrigranskning, inte verklighetsobservation eller godkänt spelprov.** Ingen Godot-, Blender-, GPU- eller nätverkskörning. Höjder nedan är lokal Y; lägg till 18 m för höjd över havet. x pekar österut, z söderut. Inga verkliga murar, tomtnivåer eller vilplan härleds ur DTM.

## Faktisk exporterad geometri

CPU-läsning av scenhierarki, nodtransformer, vertex-/indexbuffertar i `blender/world_raw.glb` och `godot/assets/world.glb`. Korridorurvalet omfattar 20 634 trianglar, inklusive fortsättningen till Norra Forsåkersgatan. Geometrin i urvalet är identisk mellan filerna; hela filernas olika SHA-256 och gemensam geometridigest finns i JSON. Detta bevisar rå-/optimerad GLB-likhet i urvalet, inte Godots importerade fysik.

Golvstrålar med högst 0,25 m avstånd längs hela Stallidenkedjan, mittlinje och ±0,65 m sidolinjer. Byggnadstak, räcken och lampor skiljs från mark. Golvet väljs bland markträffar inom ±2 m från trappans lokala referens; alla relevanta markträffar vid fogarna sparas separat. Inga strålprov saknar markyta på de tre linjerna. På vissa sidopunkter saknas själva trapprampen men terräng/gatsten fyller — därför är resultatet inget bevis på en sammanhängande kapselpassage.

| Fog, x/z | Exporterade ytor vid exakt samma XY | Betydelse |
|---|---|---|
| Roten M ↔ huvudtrappan, **87.166 / 98.474** | gatsten **23.433**, ramp **23.300** | 13,3 cm ytöverlapp. Prova från Roten M i båda riktningar och med sidoförskjutning. |
| Huvudtrappa ↔ gångväg, **28.660 / 84.937** | ramp **6.047**, gatsten **5.788** | **25,9 cm diskontinuitet**. Efter ytterligare 0,25 m nedåt är gatstenen **5.618**, totalt 42,9 cm under rampänden. 42,9 cm är inte ett enskilt lodrätt trappsteg. |
| Gångväg ↔ nedre trappa, **18.196 / 88.822** | gatsten **2.955**, ramp **2.696** | 25,9 cm skillnad mellan ytor, men gatstenen överlappar rampen en bit; hela övergången ska provas. |
| Nedre trappa ↔ parallell stig, **10.751 / 94.845** | ramp **0.645**, stig **0.490**, terräng **0.527** | 15,5 cm ramp–stig; på sydostgrenen lämnas rampen direkt och terrängen ligger **0.528** efter 1 cm. Det faktiska golvbytet är cirka 11,7 cm där. |

Spelaren har radie **0,29 m**, ståhöjd **1,76 m**, klivhjälp **0,23 m**, golvsnäppning **0,5 m** och maximal golvvinkel **55°** (`player.gd`). Särskilt 25,9 cm-fogen måste prövas uppåt med den riktiga kapseln; strålar avgör inte om klivhjälpen eller kapselns rundning tar sig över.

**Synliga steg:** täta mittlinjeprov med högst 2,5 cm avstånd hittar högst **16 cm** mellan intilliggande synliga stegtoppar på båda trappvägarna, inga högre vanliga steg i dessa prov. Synlig topp och jämn kollisionsramp skiljer högst **13,6 cm** på huvudtrappans tre provlinjer, **9,6 cm** på nedre trappans mittlinje. Däremot ligger terräng som högst **20,7 cm över rampen på huvudtrappans mittlinje**, och **50,8 cm över rampen på +0,65 m-linjen** nära **63.357 / 94.775**. Där är bild- och gånggolvet terräng snarare än den avsedda trappytan. Synliga trappräcken har ingen `COL_`-motsvarighet och kolliderar inte i nuvarande importupplägg.

## Hörn och passager

Exportens huskollisionsväggar skärs horisontellt vid 0,30 / 0,90 / 1,47 m över lokalt golv. Samma avstånd erhålls genom dessa tre höjder:

| Hus / läge på trappmittlinjen | Faktisk vägg från mittlinje | Antaget 2 m-band | Sidolinje 0,65 m mot huset, kapselradie 0,29 m |
|---|---:|---:|---:|
| **M24, w92331938**, **46.7372 / 81.4151** | **0,737 m** | hörnet går 26,3 cm in i bandet | **−20,3 cm** horisontell marginal |
| **M25, w92332157**, **54.2096 / 92.0937** | **0,943 m** | hörnet går 5,7 cm in i bandet | endast **+0,3 cm** ideal marginal |

Mittlinjens idealiska marginal är fortfarande 44,7 respektive 65,3 cm. Dessa är väggsnitt ur faktiska kollisionsmeshar; de är inte ett utfört kapselsvep. Bandets motsatta kant ligger vid antagen halvbredd 1 m, inte ett uppmätt verkligt räcke. Ingen säker fri bredd för verkliga trappan påstås.

Skärp särskilt gångprovet runt **66.237 / 105.175**, **62.526 / 94.355**, **52.699 / 91.683** och **45.391 / 80.540**. Sidolinjerna har sammanlagt nio punkter utan själva huvudtrapprampen; terräng/gatsten finns där. Nära **62.617 / 93.706** byter +0,65 m-linjen golv med **44,1 cm** höjdändring över cirka 0,25 m. Det är ett skarpt hörn-/sidoresultat, inte bevis på en verklig avsats. Byte av sidolinjens riktning i hörnet påverkar också provavståndet; kör kapseln runt svängen, inte bara mellan två fristående landningspunkter.

## Genererad site-data och OSM-spår

OSM:s `surface=sett` och vägtyper är belagda i råextraktet. **2 m bredd är pipeline-standard**, inte ett OSM-mått. Huvudtrappans många OSM-hörn är riktningspunkter; OSM har här inga uppgifter om flygter, vilplan, stegantal eller räcken.

Nedåt från Roten M är kedjan:

1. **w461711525**, trappa **74,994 m**: **87.166 / 98.474 → 28.660 / 84.937**.
2. **w461711523**, gångväg **11,162 m**: **28.660 / 84.937 → 18.196 / 88.822**.
3. **w461711524**, trappa **9,621 m**: **18.196 / 88.822 → 10.751 / 94.845**.
4. **w1227769459**, parallell gångstig mot sydost: via **26.552 / 122.062**, **34.515 / 136.233**, **39.887 / 142.278** till **47.725 / 146.030**.
5. **w1227769458**, anslutning till **Norra Forsåkersgatan w63073062** vid den gemensamma noden **47.148 / 151.117**.

Trapp-/gångkedjan till parallellstigen är **95,777 m**; fortsättningen till körbanan är **69,623 m**, totalt **165,400 m**. Den fortsättningen har också exporterade mittlinjeprov var 0,25 m, utan saknad markyta; störst höjdändring mellan dessa prov är 9,8 cm. En direkt tvärpassage från trappfoten till gatan saknar gemensam OSM-nod och ska inte räknas som verifierad förbindelse.

Site-profilen är kontinuerligt sluttande, inte en uppsättning författade vilplan. Huvudtrappan har **ingen sträcka med ≤2 % lutning**; dess längsta sträcka med ≤5 % är cirka **0,35 m**. En **4,205 m** sträcka med ≤8 % finns mellan **65.749 / 103.753** och **64.385 / 99.775**. Nedre trappan har ingen sträcka med ≤8 %. Detta beskriver den nuvarande smoothede site-profilen och bekräftar inga verkliga vilplan. Rå DTM finns i JSON som separat tolkningsunderlag, inte som föreslagna terrass-/murhöjder.

## Nästa kapselprov — fem sammanhängande områden

1. **Roten M-knuten**, w330280688 ↔ w525: börja minst 2 m in på båda anslutningarna, mittlinje och båda sidor, upp och ned.
2. **Huvudtrappans svängar och sidopassager**: hela w525 upp/ned, särskilt hörnen 66.237/105.175 och 62.526/94.355 samt M24/M25. Kör förbi husen på riktiga svängbanor med kapseln och kontrollera terränggenomslag.
3. **w525 ↔ w523**, 28.660/84.937: pröva 26 cm-fogen uppåt utan hopp samt nedåt; kontrollera båda kanter över minst 2 m.
4. **w523 ↔ w524**, 18.196/88.822: hela gatstensöverlappet och första trappmetern, inte bara den delade XY-punkten.
5. **w524 ↔ w1227769459**, 10.751/94.845, därefter sammanhängande till w1227769458 och Norra Forsåkersgatan: båda svängriktningar vid trappfoten och slutlig gatufog. Bevara skillnaden mellan parallellstig och körbana.

Alla fem behöver faktisk importerad Godot-fysik och hela upp-/nedbanor innan de kallas gångbara. Skriv inte om kvarterets verkliga mark eller bygg nya murar utifrån dessa tekniska exportfel.
