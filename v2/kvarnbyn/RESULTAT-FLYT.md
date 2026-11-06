# Helskärmsflyt — 2026-11-06

Efter Joels spelprov mättes flytet med en långsamt roterande kamera i riktig
stridsvärld. Helskärm gav en rapporterad viewport på4763×2990px på denna dator,
mycket större än den begärda fönsterytan3024×1898. Det belastade 3D-renderingen.

Nu begränsas 3D-bildens pixelantal automatiskt till cirka1920×1080 pixlar,
med bibehållet bildförhållande. UI-ytan ändras inte. Normal bild behåller samma
ljusfunktioner/material; Lägre belastning använder ytterligare0,85× skala som
förut. Budgeten räknas om vid viewportändring och kvalitetsbyte.

| Nativeprov | Genomsnitt bilder/s | 95:e percentil bildtid |
|---|---:|---:|
| Fönster, normal före |65,5|24,0ms|
| Fönster, lägre belastning före |115,1|12,3ms|
| Helskärm, normal före |31,0|51,2ms|
| Helskärm, lägre belastning före |77,1|16,3ms|
| Helskärm, normal med tak |71,6|24,3ms|

Fem sekventiella korta stickprov med nativeeditorns motor,6s uppvärmning och15s
mätning på denna M5. Andra appar var öppna. Stillastående odödlig spelare och
roterande kamera, ingen gång. Detta är inte hela kartans prestandagaranti eller
en exakt reproduktion av Joels spel. Den uppdaterade release-appen har verifierats
för budget/kvalitetsbyte, inte fått en separat full FPS-mätning.

Sex nativekontroller i exporterad app passerar: bildbudget och båda kvaliteter
vid begärda fönster-/helskärmsväxlingar. Den sista begärda återgången rapporterar
fortfarande den stora viewporten i provet; budgeten hålls även där.15 befintliga
ljus-/kvalitetskontroller passerar. Värld, kartbild, spelregler och vägnät har exakt
samma filhashar som föregående leverans. Endast runtime/upplösningshantering ändras.

**Kvarstående:** tidiga bildstopp på0,5–2,7s observerades, även med lägre kvalitet.
Takets prov har fortfarande en tidig bild på0,6s och några över33ms under mätningen.
Grundorsaken till tidiga stopp är inte fastställd. Godots dokumentation beskriver
pipelinekompilering som en möjlig källa, men sådana räknare har inte mätts här:
https://docs.godotengine.org/en/4.5/tutorials/performance/pipeline_compilations.html .
Nästa prestandaprov behöver även verklig mus/gång, andra platser och dessa räknare.

Husen blev inte mer platsriktiga av denna ändring. Se
[husstatusen](HUSSTATUS-2026-11-06.md):8egna modellvägar av381, ingen fullständig
fasad-/takverifiering. Detta är nu huvudspåret före fler botfunktioner.

[Profiler](evidence/frame-profiles-2026-11-06.json) ·
[Releasekontroller](evidence/render-scale-check-2026-11-06.json) ·
[Leveransdata](evidence/delivery-render-scale-2026-11-06.json).
