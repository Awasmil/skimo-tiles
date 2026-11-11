"""Descarga de OpenStreetMap (Overpass) los elementos con nombre para etiquetar el mapa
y buscar: picos, collados, fuentes, refugios, lagos, rios y lugares (pueblos, parajes).
Uso: python3 osm_labels.py S,W,N,E salida.geojson [cobertura.geojson]
Con cobertura: solo se guarda lo que cae dentro de la zona con relieve propio (el mapa de trabajo);
los rios se recortan a los tramos de dentro."""
import json, sys, time, urllib.parse, urllib.request
from coverage import load_coverage, inside, clip_line

bbox, out = sys.argv[1], sys.argv[2]
cov = load_coverage(sys.argv[3]) if len(sys.argv) > 3 else None
# Servidor principal y espejo publico: Overpass da 502 con frecuencia
URLS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]

def overpass(q):
    data = urllib.parse.urlencode({"data": q}).encode()
    for attempt in range(8):
        url = URLS[attempt % len(URLS)]
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": "skimo-pirineo-build/0.1"})
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.load(r)["elements"]
        except Exception as e:
            print(f"Overpass fallo ({url}), reintento:", e); time.sleep(15 * (attempt + 1))
    raise SystemExit("Overpass no responde")

points = overpass(f"""[out:json][timeout:120];(
  node["natural"~"^(peak|saddle|spring)$"]({bbox});
  node["amenity"~"^(drinking_water|water_point)$"]({bbox});
  nwr["tourism"~"^(alpine_hut|wilderness_hut)$"]({bbox});
  nwr["amenity"="shelter"]({bbox});
  nwr["natural"="water"]["name"]({bbox});
  node["place"~"^(town|village|hamlet|locality)$"]["name"]({bbox});
);out center tags;""")
lines = overpass(f"""[out:json][timeout:120];(
  way["waterway"~"^(river|stream)$"]["name"]({bbox});
);out tags geom;""")

def kind(t):
    if t.get("natural") in ("peak", "saddle", "spring"): return t["natural"]
    if t.get("amenity") in ("drinking_water", "water_point"): return "water"
    if t.get("tourism") == "alpine_hut": return "hut"
    if t.get("tourism") == "wilderness_hut": return "unguarded_hut"
    if t.get("amenity") == "shelter": return "shelter"
    if t.get("natural") == "water": return "lake"
    if t.get("waterway"): return t["waterway"]
    if t.get("place"): return "place"

def ele(t):
    try: return round(float(str(t.get("ele", "")).replace(",", ".").split()[0]))
    except (ValueError, IndexError): return None

feats = []
for e in points:
    t = e.get("tags", {}); k = kind(t)
    lon, lat = (e["lon"], e["lat"]) if "lon" in e else (e["center"]["lon"], e["center"]["lat"])
    if k == "saddle" and not t.get("name"): continue
    if cov and not inside(cov, lon, lat): continue
    props = {"kind": k, "name": t.get("name", "")}
    if ele(t) is not None: props["ele"] = ele(t)
    feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]}, "properties": props})
for e in lines:
    t = e.get("tags", {}); g = e.get("geometry") or []
    if len(g) < 2: continue
    coords = [[p["lon"], p["lat"]] for p in g]
    for part in (clip_line(cov, coords) if cov else [coords]):
        feats.append({"type": "Feature", "geometry": {"type": "LineString", "coordinates": part},
                      "properties": {"kind": kind(t), "name": t.get("name", "")}})

json.dump({"type": "FeatureCollection", "features": feats}, open(out, "w", encoding="utf-8"), ensure_ascii=False)
print(len(feats), "elementos")
