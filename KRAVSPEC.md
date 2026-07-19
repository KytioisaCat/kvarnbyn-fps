# Kravspecifikation — Försvara Kvarnbyn

Teknikoberoende kravbild för spelet. Dokumentet ska kunna ligga till grund för en
helt ny implementation eller för bedömning av en föreslagen plan, utan att binda
den till dagens teknikval. Här står *vad* som önskas och *varför det är viktigt* —
aldrig *hur* det ska byggas. Implementationsspecifika detaljer och kalibreringar
hör hemma i ARKITEKTUR.md för den implementation som råkar gälla.

Prioritetsnivåer: **Krav** (utan detta är det inte rätt produkt) ·
**Önskemål** (tydligt uttryckta önskningar, tas med när tillfälle ges) ·
**Framtida idéer** (kan komma — en ny plan bör inte omöjliggöra dem, men ska
inte leverera dem).

## 1. Vision och framgångskriterium

- **Produkten**: ett förstapersonsskjutspel som utspelar sig i ett verklighetstroget
  Kvarnbyn i Mölndal, byggt på riktig kartdata.
- **Främsta framgångskriterium ("Joel-testet")**: en person som växte upp i Kvarnbyn
  ska känna igen sig — kunna orientera sig utan karta, känna igen platser, hus,
  backar och gaturum, och spontant kunna namnge dem. **Igenkänning prioriteras över
  grafisk finess, teknisk elegans och spelbalans.** Hellre rätt siluett på fel sätt
  än snygg grafik på fel plats.
- **Designprincip**: världen ska vara verklighetstrogen; *spelmekaniken* får däremot
  vara arkadig och lustfylld — realismkravet gäller miljön, inte fysiken i spelarens
  rörelser eller vapen.
- **Målgrupp**: Joel och den närmaste kretsen. Polish för bred publik är inte ett mål;
  onboarding för främlingar behövs inte.
- **Språk**: all speltext och allt UI på svenska.
- **Rundlängd**: en runda ska ta ungefär 5 minuter (3,5–5 min för en van spelare).
- **Teknik och distribution är fria val.** Webbläsare, nedladdningsbar klient eller
  annat — bästa upplevelse vinner. (Dagens implementation är en browserlänk; det är
  ett val, inte ett krav.)

## 2. Världen

### Geografi och terräng

- **Krav**: Spelvärlden bygger på verkliga geodata över Kvarnbyn med omnejd —
  ungefär Mölndals centrum/sjukhuset i väster till Kikås/Glasberget i öster,
  några kvadratkilometer.
- **Krav**: **Realistiska höjdskillnader.** Kvarnbyns dramatiska topografi är central
  för igenkänningen: de branta gatorna, trapporna, åravinen, bergssidorna. Backarna
  ska *kännas* som i verkligheten. En lätt förstärkning av höjdskillnaderna är
  acceptabel om den stärker känslan snarare än förvanskar den.
- **Krav**: **Människobyggda plana ytor ska vara plana.** Parkeringar, torg och
  skolgårdar ska se ut och bete sig som sådana — plan yta med riktig ytkaraktär
  (beläggning, målade linjer, kantsten) — inte utsmetad flygbild över gropig mark.
  Naturen får däremot vara gropig. En parkering ska omedelbart läsas som en parkering.
- **Krav**: Mölndalsån/forsen med nedsänkt fåra, strömmande vatten som drar med sig
  och skadar spelaren i vitvatten, broar och räcken där de finns i verkligheten.
- **Krav**: Marktäcke ska gå att skilja åt visuellt på både nära och långt håll:
  asfalt, gräs, skog, berg i dagen. Skogen ska vara tät, blockera sikt och kännas
  som skog — med framkomliga stigar.

### Bebyggelse

- **Krav**: Byggnader på riktiga lägen med riktiga fotavtryck och rimliga proportioner.
- **Krav**: Kvarnbyns karaktär ska återges — vita trä- och putshus, sadeltak, de låga
  gamla arbetarstugorna i kärnan längs de branta gatorna.
- **Krav**: Hus ska kännas **unika**, inte klonade — och verklighetstrogna i den mån
  fakta går att få (färg, våningsantal, takform, material, skyltar). Det ska finnas
  en väg att successivt rätta enskilda hus mot verkligheten.
- **Krav**: Tak ska gå att beträda (spelytan omfattar hustaken).
- **Krav**: Levande gatubild: gatlyktor, parkerade bilar, vägmarkeringar, murar,
  stödmurar och räcken där terrängen kräver dem.

### Landmärken

- **Krav**: Namngivna verkliga platser ska finnas i världen och vara igenkännbara,
  skyltade och/eller visuellt särbehandlade. Minst: Gamla Torget, Roten M,
  Royens trappor, Forsebron, Kvarnbytornet, Kvarnbygatan, Götaforsliden,
  Görjelycksgatan, Störtfjället, Forsåker, Mölndals stadsmuseum, Musikskolan,
  Mölndals centrum.
- **Krav**: **Extra kärlek åt de utpekade platserna**: Corpus Pizzeria, Kråkans krog
  och Grevedämmet ska få särskild omsorg — rätt utseende, skylt på plats, detaljer
  som gör dem omisskännliga. Listan kan växa; principen är att utpekade
  barndomsplatser behandlas som hjältar, inte som vilka hus som helst.

### Ljus och stämning

- **Krav**: Dag- och kvällsläge, valbart vid start. Kvällsläget med stjärnhimmel,
  tända gatlyktor med ljusgölar och varmt lysta fönster.

## 3. Spelupplevelsen

### Scenario

- **Krav**: **Befrielsescenario**: fienden håller större delen av byn från start
  (namngivna zoner + spelarens bas). Spelaren och allierade återtar zonerna.
  Fiendens förstärkningar är villkorade av deras zonkontroll, så att zonerna har
  strategiskt värde. Basen faller = förlust; allt återtaget och rensat = seger.
- **Krav**: Spelaren respawnar vid basen; stupade allierade ersätts över tid.

### Fiender och allierade

- **Krav**: **Stort antal fiender.** Tiotals samtidigt på kartan med känsla av
  ockupation och konstant tryck; i storleksordningen 40–60 fiender totalt under
  en runda inklusive förstärkningar.
- **Krav**: Fienderna syns som soldater (modeller med animation, inte abstrakta mål),
  avancerar aggressivt, skjuter under framryckning, agerar i närstrid och tar sig
  fram utan att fastna.
- **Krav**: Allierade AI-soldater med roller (försvar respektive anfall) som deltar
  meningsfullt — kan själva ta zoner och strida.
- **Önskemål**: Fiendevariation — snabba/svaga rusare, tungt infanteri, prickskyttar
  som håller avstånd; blandning som varierar trycket.

### Rörelse

- **Krav**: Springa, sprinta, hoppa, huka (hukning ska bryta fiendens siktlinjer
  bakom skydd). Fallskada. Branta ytor begränsar framkomligheten realistiskt,
  men vägar och trappor är alltid gångbara.
- **Krav**: **Raketdubbelhopp** med doserbar kraft (kort tryck = liten skjuts,
  hållet = långt kast) — spelets signaturrörelse, arkadundantaget från realismen.

### Strid

- **Krav**: Automatkarbin med omladdning som bas; träffmarkering och tydlig feedback.
- **Önskemål**: Vapenpaket — sikte/ADS, prickskyttegevär, hagelgevär, vapenväxling.
- **Önskemål**: Granater med kastbåge och splash-skada.
- **Önskemål**: Förnödenheter — ammunition/förband vid egna zoner.

### Orientering och HUD

- **Krav**: Hälsa, ammunition, zonstatus, minikarta, händelselogg, riktningsmarkör
  mot aktuellt mål samt en taktisk fullskärmskarta över hela läget.
- **Önskemål**: Frontlinjevisning på kartorna — fiendekontrollerat område tonat med
  gränslinje och anfallsriktningar.

### Ljud

- **Krav**: Grundläggande stridsljud och forsens brus.
- **Önskemål**: Ljudlandskap — fotsteg olika per underlag, vapenljudsvarianter,
  avlägset stridsmuller när AI strider utom synhåll, vind i träden.

### Övrigt

- **Önskemål**: Poängsystem med slutstatistik och lokal highscore.
- **Önskemål**: Spelbart på mobil/pekskärm med touchkontroller (finns i dagens
  implementation och uppskattas, men får offras om en ny plattform motiverar det).
- **Önskemål**: Omstart/„spela igen" utan omladdning, mute-knapp, justerbar
  muskänslighet.
- **Krav**: Flytande prestanda på Joels vardagshårdvara (vanlig dator; telefon om
  touch-önskemålet uppfylls).

## 4. Data och juridik

- **Krav**: Kartdata, bilder och andra tillgångar ska ha licenser/villkor som
  tillåter den användning och spridning som faktiskt sker. Om spelet ligger publikt
  åtkomligt (som idag) krävs licenser som tillåter redistribution; attribution
  visas då i produkten.
- **Krav**: Inga tillgångar från källor vars villkor förbjuder ändamålet — t.ex.
  får kommersiella karttjänsters gatubilder inte bakas in som texturer eller
  modelldata, oavsett hur bra de vore. (Att *titta* på dem som mänskligt
  referensmaterial vid handförfattande av husfakta är okej; systematisk skörd
  eller pixlar in i produkten är det inte.)
- **Krav**: Inga inloggningsuppgifter eller API-nycklar i repo, filer eller chat.

## 5. Framtida idéer (ska inte omöjliggöras)

- **Historiskt läge**: samma by med historiska flygbilder från 1960–1999 —
  barndomens Kvarnbyn som spelbar värld.
- **Riktiga fasader**: fasadtexturer från egna foton och/eller fotogrammetri av
  kärnkvarteren (drönare).
- **Multiplayer/co-op**.
- Öppet licensierade gatufoton (t.ex. Mapillary, CC BY-SA) som källa för husfakta
  och utvalda fasadtexturer, om täckning finns.

## 6. Acceptanstest

1. **Joel-testet**: Joel kan orientera sig från basen till valfritt landmärke utan
   att öppna kartan, och känner spontant igen gaturummen längs vägen.
2. Samtliga landmärken i avsnitt 2 är identifierbara i spel; Corpus Pizzeria,
   Kråkans krog och Grevedämmet är omisskännliga.
3. En parkering ser ut som en parkering — plan, med linjer — inte som färgad backe.
4. En van spelare vinner en runda på 3,5–5 minuter; trycket från fienden känns
   konstant men inte hopplöst.
5. Backarna känns: att springa uppför Götaforsliden eller Royens trappor ska
   märkas i benen (farten) och i ögonen (vyn).

---

# Anskaffade tillgångar

Separat inventarie över data, filer och rättigheter som redan finns. **En ny
implementation är inte skyldig att använda något av detta** — listan finns för
att slippa anskaffa om sådant som redan är löst, och för att visa vad som är
möjligt utan nya beställningar.

| Tillgång | Innehåll | Licens/villkor |
|---|---|---|
| Ortofoto 0,16 m (Lantmäteriet, flygår 2024) | Råa GeoTIFF-rutor i lokal cache + sammansatta bilder upp till 8192 px över hela området | CC BY 4.0 — attribution krävs |
| Markhöjd LiDAR 1 m (Lantmäteriet) | GeoTIFF-rutor + sammansatt höjdgrid (~2144×1447 celler à 1 m) — innehåller riktiga murar, trappor, branter | Öppna data (CC0) |
| Geotorget-konto med godkända produktbeställningar | Rätt att ladda ner ovanstående igen samt **historiska ortofoton 1960–1999 ur samma API** (nyckeln till historiskt läge) | Per produkt; konto = Joels |
| OSM-extrakt över området | ~1 660 byggnadsfotavtryck (med typ, 34 namngivna), vägnät, murar, skogspolygoner, ~170 parkeringsytor, vattenpolygoner, POI:er; sparad Overpass-fråga → reproducerbart/uppdaterbart | ODbL |
| Härledd markklassningskarta | Asfalt/gräs/skog/berg per 2 m-cell, byggd ur foto + LiDAR + OSM | Härledd ur ovanstående |
| Takfärg per byggnad | Samplad ur ortofotot per fotavtryck | Härledd ur ortofotot |
| Landmärkeslista med koordinater | Namngivna platser med positioner + enkel lat/lon↔spelkoordinat-mappning | Egen |
| Python-datapipeline (`tools/`) | Källdata → speldata (terräng, hus, vägar, klasskarta); motoroberoende till sin natur — in: öppna geodata, ut: geometri och attribut | Egen kod |
| Referensimplementationen | Dagens spelbara spel — facit för känsla, balans och beteenden vid bedömning av en ny plan | Egen kod (three.js MIT vendorerad) |
| Dokumenterad domänkunskap | ARKITEKTUR.md (beslut med motiv, kalibreringar, dyrt inlärda fällor), TODO.md, CLAUDE.md | Egen |
| Ev. promenadfoton hos Joel | Fasadfoton med GPS/EXIF från promenader (omfattning obekräftad) | Egna foton |
| Distributionskanal | GitHub-repo + automatisk publicering till webblänk | — |
