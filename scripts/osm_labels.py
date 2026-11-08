"""Descarga de OpenStreetMap (Overpass) los elementos con nombre para etiquetar el mapa
y los guarda como GeoJSON: picos, collados, fuentes, refugios, lagos y rios.
Uso: python3 osm_labels.py S,W,N,E salida.geojson"""
import json, sys, time, urllib.parse, urllib.request

bbox, out = sys.argv[1], sys.argv[2]
URL = "https://overpass-api.de/api/interpreter"

def overpass(q):
    data = urllib.parse.urlencode({"data": q}).encode()
    for attempt in range(4):
        try:
            req = urllib.request.Request(URL, data=data, headers={"User-Agent": "skimo-pirineo-build/0.1"})
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.load(r)["elements"]
        except Exception as e:
            print("Overpass fallo, reintento:", e); time.sleep(20 * (attempt + 1))
    raise SystemExit("Overpass no responde")

points = overpass(f"""[out:json][timeout:120];(
  node["natural"~"^(peak|saddle|spring)$"]({bbox});
  nwr["tourism"~"^(alpine_hut|wilderness_hut)$"]({bbox});
  nwr["amenity"="shelter"]({bbox});
  nwr["natural"="water"]["name"]({bbox});
);out center tags;""")
lines = overpass(f"""[out:json][timeout:120];(
  way["waterway"~"^(river|stream)$"]["name"]({bbox});
);out tags geom;""")

def kind(t):
    if t.get("natural") in ("peak", "saddle", "spring"): return t["natural"]
    if t.get("tourism") == "alpine_hut": return "hut"
    if t.get("tourism") == "wilderness_hut": return "unguarded_hut"
    if t.get("amenity") == "shelter": return "shelter"
    if t.get("natural") == "water": return "lake"
    if t.get("waterway"): return t["waterway"]

def ele(t):
    try: return round(float(str(t.get("ele", "")).replace(",", ".").split()[0]))
    except (ValueError, IndexError): return None

feats = []
for e in points:
    t = e.get("tags", {}); k = kind(t)
    lon, lat = (e["lon"], e["lat"]) if "lon" in e else (e["center"]["lon"], e["center"]["lat"])
    if k == "saddle" and not t.get("name"): continue
    props = {"kind": k, "name": t.get("name", "")}
    if ele(t) is not None: props["ele"] = ele(t)
    feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]}, "properties": props})
for e in lines:
    t = e.get("tags", {}); g = e.get("geometry") or []
    if len(g) < 2: continue
    feats.append({"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[p["lon"], p["lat"]] for p in g]},
                  "properties": {"kind": kind(t), "name": t.get("name", "")}})

json.dump({"type": "FeatureCollection", "features": feats}, open(out, "w", encoding="utf-8"), ensure_ascii=False)
print(len(feats), "elementos")
