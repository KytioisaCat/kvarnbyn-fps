# Exporterbar materialfinish och fönsterprov

## Använd i huvudbygget

Efter att materialordboken `M` skapats, före geometrin:

```python
from blender_finish import apply_finish
apply_finish(M)
```

- `panel`, `cream`, `plaster`: tonmatchade fotografiska albedovarianter med
  ±5,5–6,5 % linjär ljusvariation. De ursprungliga normal-/roughnesskartorna
  behålls. Ingen brun smutsfärg läggs till.
- `metal`: målad plåt med ±7,5 % diskret pigmentvariation och roughness 0,505–0,615.
  UV-skala är 4 m, därför ska hjälparen användas före geometribygget.
- `grass`: samma CC0-markfoto med bevarad småskalig detalj och en måttligare svensk
  tidigsommarpalett. Medel-RGB går från ungefär 110/96/62 till 99/113/63.
  Det är en säsongstolkning, inte uppmätt vegetation eller markklassning.

Bilderna är 1k och vanliga bildtexturer kopplade till Principled BSDF. Källor,
bearbetning och mätvärden finns i `manifest.json`; ursprungslicensen är CC0.
Förbered om varianterna med:

```
tools/venv/bin/python v2/poc/torget/assets-src/blender_finish.py --prepare
```

`material_comparison.png` visar albedot före/efter. `after_krakan.png` och
`after_oversikt.png` är Cycles-prov från en kopia av den tidigare sparade scenen;
originalet sparades inte och senare geometrirättningar ingår därför inte där.
`QA.json` bekräftar att panelens färg/normal/roughness och plåtens färg/roughness
överlever glTF-export.

## Fysiska interiörproxies

I `modelkit.window()`, bakom den enkelsidiga glasytan:

```python
from blender_windows import add_interior
add_interior(kit, name, at, u, outward, width, height,
             door=door, variant=stable_variant)
```

`at(a, depth, h)` är kitets samma lokala-till-världs-funktion: horisontell position,
djup positivt mot gatan och höjd från fönstrets botten. Väggöppningen måste vara
verklig. Baksidan ligger vid djup −0,08 m, gardiner vid 0…+0,005 m och framglaset
kan ligga vid +0,025 m. Det är en grund visuell kavitet, inte spelbara rum.

Tre stabila lägen:

| variant | Innehåll | Trianglar för interiören |
|---|---|---:|
| 0 | Två delvis fördragna gardiner med sju geometriska veck per sida | 122 |
| 1 | Delvis neddragen persienn med tolv snedställda lameller och tunna snören | 40 |
| 2 | Mörk klar interiör | 10 |
| valfri + `door=True` | Entré-/butiksdörr utan gardiner eller persienn | 10 |

Alla interiörmaterial är opaka, enkla Principled-material. Använd gärna
`kit.window_batch_name = 'WindowInteriors'` för att slå ihop opaka interiörer över
husen per material och hålla antalet anrop nere. `make_window_materials()` skapar
materialen en gång; de kan även läggas i `kit.window_materials`.

`windows_qa.png` visar en separat testvägg med riktiga öppningar och alla tre
lägen plus entré. Framglaset där är enkelsidigt, alpha 0,20 och roughness 0,10.
Alla lägen har kontrollerats för geometribudget och djupgränser; materialexport
är verifierad i det lokala QA-provet. Transparensens sortering, skuggor och
prestanda måste dessutom bedömas i Godot på telefonen. Ingen fejkad rumslampa
eller bakad ljusgradient ingår.
