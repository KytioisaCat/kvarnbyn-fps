# Fotografisk Pure Sky-proxy

**Kloofendal 48d Partly Cloudy (Pure Sky)** från Poly Haven, 1k Radiance HDR,
**1 435 119 bytes**. Upphov: Greg Zaal (foto), Jarod Guest (sky-only-bearbetning).
Licens: **CC0-1.0**. Exakt källa, käll-URL, MD5 och SHA256 finns i `manifest.json`.

Detta är en **generisk daghimmelproxy**, inte den verkliga himlen över Kvarnbyn.
Originalet fotograferades i Sydafrika; Pure Sky-versionen har redigerats till
bara himmel och saknar den geografiska miljön/horisonten. Vitbalansen är neutral
5400 K, inte varm kväll. Panorama: 1024 × 512, equirektangulärt, linjär HDR.

`sky_preview_agx.png` är en tonmappad granskningsbild (AgX, Medium High Contrast,
−0,5 steg). Använd **.hdr-filen**, inte PNG-förhandsbilden, för ljus och himmel:

- Blender: Environment Texture → Background → World Output.
- Godot: PanoramaSkyMaterial i en Sky-resource. Godot-importen av HDR ska behålla
  HDR-formatet; verifiera energin mot spelets miljöinställningar.

Panoramat innehåller en stark fotograferad sol vid ungefär 48° höjd. Om en separat
riktad sol behålls ska dess riktning och energi balanseras mot HDRI:t så att
belysningen inte ger motstridiga riktningar. Manifestets `brightest_pixel_uv_bottom_up`
ger ljusaste pixelns panoramakoordinat för orienteringshjälp; yaw-konventionen måste
anpassas till respektive motor. Ingen scen ändrades av denna assetleverans.
