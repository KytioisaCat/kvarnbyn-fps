# Stalliden — integration av den fristående modulen

`pipeline/stalliden.py` gör inga filskrivningar. Fryst föreunderlag finns i `data-review*`; nya CPU-prov finns i `qa-stalliden.*`. DTM-höjder, bredder och flykt-/vilplansdelning är uppskattningar. Den granskade bilden från 2017 stödjer materialkaraktär och korta trapplopp med gångytor emellan, inte dessa exakta mått.

```python
from stalliden import StallidenGround

old_band = StallidenGround.original_domain(city)
# original_urban innehåller befintliga färdiga markytor, inklusive parallellstigen.
# cut är hus/vatten/broar. original_domain undantar uttryckligen parallellstigen
# och Norra Forsåkersgatan så de aldrig råkar tas bort med gamla trappans ändlock.
blocked = cut.union(original_urban.difference(old_band))
stalliden = StallidenGround(city, blocked, work, raw_height,
                           finished_reference.height, Y_OFFSET)
```

`finished_reference` ska läsa de **ursprungliga triangulerade** asfalt-/sten-/gång-/stigytorna med deras befintliga lift inräknad. För `SurfaceReference`: `lift=0`, callbackens resultat är då färdig råhöjd. Fallback till DTM är endast reserv utanför de faktiska ytorna.

Ta `replacement_domain` ur gamla markmeshar och utelämna de gamla generiska trapporna **w461711525 och w461711524**, inklusive deras gamla räcken. Bevara alla andra ytor. Av Roten M **w330280688** ersätts endast de sista fyra metrarna mot Stalliden; M29:s anslutningar längre bort lämnas orörda.

Triangulera varje post i `surfaces` separat med dess `height_fn` och **lift 0**. `render=False/collision_only=True` betyder en osynlig flyktramp som måste ha COL och räknas i terrängklippningen. Synliga trappor kommer från `stairs[].treads`, med explicit `top_y`, `bottom_y` och konturer. De ska inte få den gamla extra 2-centimetersliften eller kvantiseras till en annan 16-centimetersserie. `riser_m` når de gemensamma slutnivåerna exakt och är högst cirka 16,4 cm.

`rails` har färdiga lokala fotpunkter, höjd, radie och kollisionsbredd. Riktiga offsetkurvor runt hörnen lämnar den numeriska mittkorridoren fri. Bygg både render och verklig räckeskollision. Ett slutet räckesprov och en fri gångpassage finns i `metadata()['ground_checks']['blockers']`.

Klipp gamla terrängtrianglar exakt under `coverage`. `supports` är endast tekniska slutytefyllningar längs den nya volymens ytterkant, med topp/botten per endpoint i lokal Y; de är **inte observationer av verkliga murar**. Sänk gärna botten ytterligare mot den gamla konformerade terrängytan. Borttagna delar av de gamla tvåmetersbanden behöver mjuk terrängövergång: största analytiska sidodifferens mot rå DTM är cirka **1,46 m vid 64,491 /97,925**. Detta kräver faktisk bild-/meshkontroll och ger inget stöd för en hög ny M31-mur.

Spara hela `metadata()` exempelvis i `site['stalliden']`, och dess `ground_checks` i `world_meta['stalliden_ground_checks']`. Punkter och banor använder färdig lokal Y, inte kamerans ögonhöjd. Banorna går från Roten M hela vägen till den korta uppskattade fotgängaranslutningen mot Norra Forsåkersgatan och tillbaka. Testa den verkliga kapseln i båda riktningar utan omplacering; mät särskilt nedre trappans sneda möte med den bevarade parallellstigen.

All motorprovning är ljudlös: `--audio-driver Dummy`. Inga motor-/GPU-processer har startats av modul-/CPU-granskningen. Slutlig exporterad geometri och importerad fysik återstår som huvudagentens integrationsgrind.
