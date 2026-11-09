# Götaforslidens entréer — platsprov 2026-11-09

Street View faktiskt granskad från både nedre och övre sidan av G18. Panorama-id,
datum, riktningar och observationer i `entrance.json`. Ingen fotopixel i spelet.

G18 har en lång upphöjd betongplattform vid den gulgröna dörren, ljusa enkla
räcken, naturstensgrund och spaljé runt övre hörnet. Första provet bygger själva
plattformen och tvåliggarräcket; spaljé, värmepump och smådetaljer återstår.
Alla mått och anslutningssteg är uppskattningar. Fyra steg i slutprovet är en funktionell
anpassning mellan dörrtröskeln och levererad gatuhöjd, inte en observerad
stegräkning bakom spaljén. Stegprovet ska bedömas med detta förbehåll.

Lokala vägförskjutningen ger utrymme mellan plattform och G17 utan att flytta
OSM-husen. Samma linje används för asfalt/kollision/karta/nav. G18:s generiska
ensamma dörrplatta ersätts av plattformens sammanhängande yta.

`gotafors_details.py` bygger synliga och fysiska ytor från samma värden. Platsens
metadata provas med riktiga golvstrålar, spelarkapsel till/från dörren och räcket.
`--entrance-export-check` återanvänder samma kontroll som gaturundorna med ett
annat metadatafält. `verify_roten.gd --check-key=gotafors_ground_checks` ger ett
utförligare prov. Geometri-QA läser också de exporterade plattforms-/stegytorna.

G17:s L-form behöver fortsatt avläsning per delfasad. Uppströmsfasaden har gröna
portar/överljus och låga steg. Första provets globala vånings-/sockelnivåer räcker
inte för att hävda exakta dörrhöjder längs hela backen. Parkeringar, planteringar
och fler hus behandlas i följande delpass; de är inte färdigmodellerade här.
