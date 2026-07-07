import json, time, urllib.request

LAT0, LAT1 = 57.6495, 57.6625
LON0, LON1 = 12.008, 12.044
ROWS, COLS = 56, 84  # ~26m spacing

pts = []
for r in range(ROWS):
    lat = LAT0 + (LAT1-LAT0)*r/(ROWS-1)
    for c in range(COLS):
        lon = LON0 + (LON1-LON0)*c/(COLS-1)
        pts.append((lat,lon))

elev = []
BATCH = 100
for i in range(0, len(pts), BATCH):
    batch = pts[i:i+BATCH]
    locs = "|".join(f"{la:.6f},{lo:.6f}" for la,lo in batch)
    url = f"https://api.opentopodata.org/v1/eudem25m?locations={locs}"
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=30) as f:
                d = json.load(f)
            elev.extend([r["elevation"] for r in d["results"]])
            break
        except Exception as e:
            print(f"batch {i//BATCH}: retry {attempt} ({e})")
            time.sleep(3)
    else:
        raise SystemExit("failed")
    print(f"batch {i//BATCH+1}/{(len(pts)+BATCH-1)//BATCH} done")
    time.sleep(1.1)

json.dump({"rows":ROWS,"cols":COLS,"lat0":LAT0,"lat1":LAT1,"lon0":LON0,"lon1":LON1,"elev":elev}, open("elevation.json","w"))
vals = [e for e in elev if e is not None]
print(f"min {min(vals):.1f}m max {max(vals):.1f}m")
