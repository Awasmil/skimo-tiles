"""Senderos senalizados de OpenStreetMap (relaciones route=hiking/foot: GR, PR, SL, caminos locales)
recortados a la zona de trabajo del mapa.
Uso: python3 osm_routes.py S,W,N,E salida.geojson [cobertura.geojson]"""
import json, sys, time, urllib.parse, urllib.request
from coverage import load_coverage, clip_line

URLS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]

def overpass(q):
    data = urllib.parse.urlencode({"data": q}).encode()
    for attempt in range(8):
        url = URLS[attempt % len(URLS)]
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": "skimo-pirineo-build/0.1"})
            with urllib.request.urlopen(req, timeout=240) as r:
                return json.load(r)["elements"]
        except Exception as e:
            print(f"Overpass fallo ({url}), reintento:", e); time.sleep(15 * (attempt + 1))
    raise SystemExit("Overpass no responde")

bbox, out = sys.argv[1], sys.argv[2]
cov = load_coverage(sys.argv[3]) if len(sys.argv) > 3 else None

rels = overpass(f"""[out:json][timeout:180];(
  relation["route"~"^(hiking|foot)$"]({bbox});
);out geom;""")

COL = {"red": "#d7191c", "white": "#d7191c", "yellow": "#e6a800", "green": "#2ca25f", "blue": "#2b6cb0",
       "orange": "#f07c00", "purple": "#7b3294", "black": "#333333", "brown": "#8c510a"}

def colour(t):
    ref = (t.get("ref") or "").upper().replace(" ", "")
    if ref.startswith("GR"): return "#d7191c"      # GR: rojo y blanco
    if ref.startswith("PR"): return "#e6a800"      # PR: amarillo y blanco
    if ref.startswith("SL"): return "#2ca25f"      # SL: verde y blanco
    way = (t.get("osmc:symbol") or "").split(":")[0].strip().lower()
    return COL.get(way, "#7b3294")

feats = []
for r in rels:
    t = r.get("tags", {})
    name, ref = t.get("name", ""), t.get("ref", "")
    if not (name or ref): continue
    label = f"{ref} · {name}" if ref and name and ref not in name else (name or ref)
    props = {"name": label, "ref": ref, "network": t.get("network", ""), "col": colour(t)}
    for m in r.get("members", []):
        g = m.get("geometry")
        if m.get("type") != "way" or not g or len(g) < 2: continue
        coords = [[p["lon"], p["lat"]] for p in g if p]
        for part in (clip_line(cov, coords) if cov else [coords]):
            feats.append({"type": "Feature", "geometry": {"type": "LineString", "coordinates": part}, "properties": props})

# Todos los caminos (no solo los senalizados): sendas, pistas, caminos de herradura, escaleras
SAC = {"hiking": "T1", "mountain_hiking": "T2", "demanding_mountain_hiking": "T3", "alpine_hiking": "T4",
       "demanding_alpine_hiking": "T5", "difficult_alpine_hiking": "T6"}
ways = overpass(f"""[out:json][timeout:180];(
  way["highway"~"^(path|footway|track|bridleway|steps)$"]({bbox});
);out tags geom;""")
npaths = 0
for w in ways:
    t, g = w.get("tags", {}), w.get("geometry") or []
    if len(g) < 2 or t.get("access") in ("private", "no"): continue
    hw = t["highway"]
    props = {"kind": "track" if hw == "track" else "path", "name": t.get("name", ""), "sac": SAC.get(t.get("sac_scale", ""), "")}
    coords = [[p["lon"], p["lat"]] for p in g if p]
    for part in (clip_line(cov, coords) if cov else [coords]):
        feats.append({"type": "Feature", "geometry": {"type": "LineString", "coordinates": part}, "properties": props}); npaths += 1
print(npaths, "tramos de caminos")
for f in feats: f["properties"].setdefault("kind", "route")

json.dump({"type": "FeatureCollection", "features": feats}, open(out, "w", encoding="utf-8"), ensure_ascii=False)
print(len(rels), "rutas,", len(feats), "tramos")
