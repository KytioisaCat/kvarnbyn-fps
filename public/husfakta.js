// Husfakta — hur enskilda hus i Kvarnbyn SER UT, som data. Läses av game.js (factsFor).
//
// Arbetssätt: titta på foton (egna promenadfoton, Street View, Mapillary) som mänskligt
// referensmaterial och beskriv huset här i JSON. Aldrig bilder/pixlar från karttjänster in i
// spelet (KRAVSPEC §4) — bara fakta i ord. Kandidatlista med länkar att titta på genereras av
// `python3 tools/husfakta_lista.py` → tools/husfakta_kandidater.md.
//
// Nyckel: "w<OSM-way-id>" (säkrast) eller adress som i OSM, t.ex. "Kvarnbygatan 12".
// Fält (alla valfria, svenska):
//   farg      fasadkulör: "#f3e6b0", CSS-namn ("lightyellow") eller svenskt namn
//             (vit, gul, ljusgul, röd, faluröd, grå, ljusgrå, beige, brun, grön, mörkgrön,
//              blå, rosa, ockra, tegelröd, terrakotta, svart)
//   vaningar  antal våningar (höjd = våningar × 3 m + 1,5 m tak/sockel) — slår OSM-gissning
//   hojd      byggnadshöjd i meter (om våningar inte passar)
//   tak       "sadel" | "platt"
//   takfarg   takkulör (annars samplas den ur flygfotot)
//   material  "tra" (panel) | "puts" | "tegel" | "plat" | "glas"
//   skylt     text som sätts på fasaden mot närmaste gata (skyltar, namn, verksamhet)
//   kommentar fri text för människor; kalla = varifrån fakta kommer
//
// OSM-taggar (building:levels, building:colour, roof:shape, building:material) läses automatiskt
// ur data.js och gäller om inget står här. Det som står här vinner alltid.
window.KVARNBYN_HUSFAKTA = {
  // ---- hjältehusen (KRAVSPEC §2: "extra kärlek åt de utpekade platserna") ----
  "w92332103": {
    "skylt": "Corpus Pizzeria",
    "kommentar": "Huset som innehåller OSM-noden Corpus Pizzeria (fast_food). Kulör/våningar: fyll i efter foto.",
    "kalla": "OSM POI-nod 463940910"
  },
  "w92331981": {
    "skylt": "Kråkans Krog",
    "kommentar": "Huset som innehåller OSM-noden Kråkans Krog (restaurant), vid Götaforsliden.",
    "kalla": "OSM POI-nod 463940899"
  },
  "w48115243": {
    "skylt": "Mölndals stadsmuseum",
    "kommentar": "Kvarnbygatan 12. OSM: 4 våningar (läses automatiskt).",
    "kalla": "OSM way (name, building:levels)"
  },
  "w613091855": {
    "skylt": "Kulturhuset Möllan",
    "kalla": "OSM way (name)"
  },
  "w90143419": {
    "skylt": "Villa Korndal",
    "kommentar": "Kvarnbyvillan.",
    "kalla": "OSM way (name)"
  },
  "w92332149": {
    "skylt": "Lilla Götafors",
    "kommentar": "Götaforsliden 15.",
    "kalla": "OSM way (name)"
  },
  "w92331982": {
    "skylt": "Hembygdsföreningen",
    "kommentar": "Mölndals Hembygdsförening, Royens gata 8. OSM: 2 våningar.",
    "kalla": "OSM way (name, building:levels)"
  },
  "w97094342": {
    "skylt": "Hemvärnsgården",
    "kommentar": "Delbancogatan 10B.",
    "kalla": "OSM way (name)"
  }
};
