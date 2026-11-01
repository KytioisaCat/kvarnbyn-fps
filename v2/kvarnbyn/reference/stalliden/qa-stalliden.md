# Oberoende CPU-QA — StallidenGround

2026-11-01. **Fristående modul-QA är grön: 13 av 13 kontroller.** Detta gäller analytiska ytor och metadata före triangulering/export. Importerad Godot-geometri och faktisk kapselgång är inte testade här.

Modulens SHA-256: `203ec611d5fedd750573b2c658db0e04b4c316fe8ffb75e9ccc2c186665c5347`. City-/site-hashar och exakta resultat finns i `qa-stalliden.json`. Baselinefilerna `data-review*` har lämnats orörda. Återkör med `tools/venv/bin/python v2/kvarnbyn/reference/stalliden/qa-stalliden.py` mot samma underlag.

Ytor och bredd beräknas oberoende från geometrierna; inga slutresultat hämtas ur den temporära `data-review.new-profile-qa.json`. Ankarreferensen byggs från alla befintliga asphalt/paving/walkway/trail-trianglar med `SurfaceReference`, offset 18 m och lift 0. Förbjuden geometri är hus/vatten/broar och befintlig urban utanför `original_domain`.

| Kontroll | Resultat |
|---|---|
| Omfattning | 147,3852718 m², 21 disjunkta ytor, 16 trappflygter, 128 synliga steg, två räckeskedjor |
| Fyra ankare, rå färdig höjd | **41,433060619 / 23,788434644 / 20,955283583 / 18,490215902 m**; exakt inom 1 µm |
| Hus och orelaterad urban | Ingen areaöverlapp; numeriskt brus <10⁻¹⁵ m² |
| Utanför coverage | **182 262 punkter exakt oförändrade**, prövade med oberoende artificiell originalhöjd |
| Inre materialsömmar | 20 sömmar med täta kantprov; största skillnad **1,898 cm** mellan huvudtrappans landning och Roten-landningen. Gånglänkens båda trappanslutningar har noll skillnad. |
| Mittlinje och sidoband | 19 175 prov, högst 2,5 cm stationavstånd, sidolägen **−0,49 / −0,20 / 0 / +0,20 / +0,49 m** på huvudtrappa/gånglänk/nedre trappa. Samtliga täcks av nya ytor eller faktisk bevarad urban; **184 prov på nedre slutanslutningen använder den bevarade gamla stigen**. Största intilliggande höjdändring **8,614 cm**. |
| Synliga steg | Högsta författade steg **16,390 cm**; treden kolliderar inte, separat ramp är gånggolv. |
| M24/M25 | Klippt tvärbredd **1,38979 / 1,40000 m**. Båda täcker den prövade kroppskorridoren ±0,49 m. |
| Räcken | Minsta avstånd från mittlinje **0,636859 / 0,636918 m**. Ingen geometrisk överlapp med mittkorridor ±0,20 m plus kapselradie 0,29 m och räckeskolliderhalvbredd 0,035 m. |
| Blocker-metadata | `blocked=true` korsar räckesbandet; `blocked=false` lämnar gånglänken fri i 2D. 3D-prov mot exporterade stolpar/räcken återstår. |
| Bevarade urbana klippkanter | Största höjdskillnad **10,083 cm** över en 4 mm kantnormal vid nedre trappans övergång till bevarad stig, inom 23 cm-gränsen. Connectorns egna **28 kantprov** skiljer högst **0,547 mm**. |
| Hela metadata-banorna | Upp/ned, 5 511 punkter per riktning. Största steg **9,262 cm** ligger på befintlig Roten M utanför de nya sista fyra metrarna. Utanför nya ytor används den gamla färdiga golvreferensen i detta enhetsprov. |

Den första räckesversionen skar hörn och nådde 0,410 m från mittlinjen; den prövade slutversionens `offset_curve`-geometri löser det. Den sista gånglänks-/connectorjusteringen ger nu sammanfallande trappanslutningar och lokal anknytning till bevarade gatu-/stigkanter.

## Randfix verifierad; terrängintegration återstår

**Den tidigare 0,175 m-randen är löst i masken.** `original_domain()` undantar nu parallellstigens och körbanans bevarade band. De åtta tidigare provpunkterna **10.133008 / 95.222172 → 9.983838 / 95.313213** tas därför inte längre bort ur den gamla stigen. Hela upp-/nedbanan har nu **noll punkter inom borttagen gammal mask men utan ny yta**. Att slutet av nedre trappbanan använder bevarad stig är avsiktligt och redovisas separat i JSON; det är inte ett hål i golvet.

**Sidomarginalen kräver terrängövergång.** Det nya underlaget skiljer som mest **1,460 m från rå DTM** nära **64.490596 / 97.925423**, inom gammalt ersättningsband. Det är diagnostik för terrängklippning/feather och slutna tekniska stöd, inte bildstöd för en verklig mur. Ny höjd ska inte läggas ovanpå gammal terräng där.

Nästa avgörande prov är faktiska exporterade trianglar: gamla ersättningsband/trappor borttagna, bevarad parallellstig intakt, terräng under nya gångytor, slutna stöd samt fungerande räckeskollider. Därefter hela upp-/nedbanorna och M24/M25 med den riktiga spelarkapseln, ljudlöst i Godot.

Källmärkningen skiljer observerat material/korta lopp/enkel ledstång i den granskade 2017-bilden från **uppskattade** höjder, bredder, flygtantal, placeringar och direktconnector. Modulen bygger ingen M31-mur.
