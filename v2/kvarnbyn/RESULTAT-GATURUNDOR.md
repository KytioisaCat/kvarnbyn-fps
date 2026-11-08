# Gaturundor — första delpasset, 2026-11-08

13felaktigt utvidgade huskonturer är återställda. Tre lokala gator har bättre
linjeföring, bredd, stenbård och sammanhängande infart. Fyra fasader har rättats
mot faktiskt granskad Street View: Götaforsliden17/18, Royens1 och det västra
huset vid Franckegatan. Inga Street View-bilder används som speltexturer.

## Vad som orsakade väg-/husfelen

Vägmarken klipptes mot ursprungliga OSM-hus, medan husbyggaren gjorde vissa
oregelbundna konturer större genom rektangelförenkling. Kontroll av levererade
marktrianglar hittade12intrång, cirka21,9m². Nu används samma byggkontur för
hus, markklippning och kollision. Grunddatahusens positioner är bevarade.

Tre granskade trånga vägpartier är lokalt korrigerade och uppskattade till
2,7/3,2/3,0m. Gatornas övergångar och alla anslutningar följer med. Royens gata
har gatsten enligt både synlig referens och OSM, de två andra asfalt med låg
stenbård. Det är lokal bildtolkning, inte ny lantmäteriinmätning.

## Prov och kvarstående osäkerhet

381hus och352vägar granskas i geometri-/nätkontrollen. Synliga/kolliderande
vägtrianglar matchar aktuell byggdata och varandra. Inga intrång hittas även
när författade gångytor, trappor och brodäck ingår. Nio markpunkter, tre stråk
åt båda håll och tre husstopp provade med riktig kapsel;19motsvarande prov
finns även inne i releasepaketet.180globala markpunkter, äldre plats-/krok-/
spelprov och nativebilder kompletterar detta. Två botrundor gav tidsgräns600s
respektive förlust220,2s; inga balansändringar och inget segerpåstående.

Tak och dolda sidor är fortsatt osäkra. G18:s entréplattform, G17:s entré/tak,
Franckehusets högre bakdel och större delen av övriga staden kräver fortsatt
arbete. Inga hus är färdigbedömda enbart för att en geometrigrind passerar.
Joels igenkänningsomdöme väger tyngst. Nästa område är startkvarteren vid
övre Görjelycksgatan; fortsatt iterering är uttryckligen beställd.

Referenser: `reference/vag-hus/README.md`, `reviews.json` och de namngivna
`evidence/road-*.json`. Före/slutbilder ligger lokalt i `evidence/roads/`.
Leveranskvitto: `evidence/delivery-roads-2026-11-08.json`.
