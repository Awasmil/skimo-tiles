"""Red de caminos de OpenStreetMap (Overpass) para que el medidor siga senderos en el movil.
Salida JSON compacta:
  {"n": [[lon,lat],...]  (vertices: cruces y extremos, en 1e-5 grados enteros)
   "e": [[a, b, metros, [lon0,lat0,dlon1,dlat1,...]], ...]}  (tramos; coords en 1e-5 enteros, deltas tras la primera)
Uso: python3 paths_graph.py S,W,N,E salida.json"""
import json, math, sys, time, urllib.parse, urllib.request

bbox, out = sys.argv[1], sys.argv[2]
URLS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
HW = "path|footway|track|bridleway|steps|cycleway|pedestrian|unclassified|service|residential|living_street|tertiary|secondary|primary"

def overpass(q):
    data = urllib.parse.urlencode({"data": q}).encode()
    for attempt in range(8):
        url = URLS[attempt % len(URLS)]
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": "skimo-pirineo-build/0.1"})
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.load(r)["elements"]
        except Exception as e:
            print(f"Overpass fallo ({url}), reintento:", e); time.sleep(15 * (attempt + 1))
    raise SystemExit("Overpass no responde")

ways = [w for w in overpass(f'[out:json][timeout:240];way["highway"~"^({HW})$"]({bbox});out body geom;')
        if w.get("type") == "way" and len(w.get("nodes", [])) >= 2 and len(w.get("geometry", [])) == len(w["nodes"])]

def dist(a, b):
    r = math.pi / 180
    x = (b[0] - a[0]) * r * math.cos((a[1] + b[1]) / 2 * r)
    y = (b[1] - a[1]) * r
    return 6371008.8 * math.hypot(x, y)

use = {}
for w in ways:
    for i, nid in enumerate(w["nodes"]):
        use[nid] = use.get(nid, 0) + (2 if i in (0, len(w["nodes"]) - 1) else 1)

vid, nodes, edges = {}, [], []
def vertex(nid, g):
    if nid not in vid:
        vid[nid] = len(nodes); nodes.append([round(g["lon"] * 1e5), round(g["lat"] * 1e5)])
    return vid[nid]

for w in ways:
    ns, gs = w["nodes"], w["geometry"]
    start, coords, length = 0, [[gs[0]["lon"], gs[0]["lat"]]], 0.0
    for i in range(1, len(ns)):
        p = [gs[i]["lon"], gs[i]["lat"]]
        length += dist(coords[-1], p); coords.append(p)
        if use[ns[i]] > 1 or i == len(ns) - 1:
            a, b = vertex(ns[start], gs[start]), vertex(ns[i], gs[i])
            q = [(round(c[0] * 1e5), round(c[1] * 1e5)) for c in coords]
            # Delta: primera coordenada absoluta, el resto diferencias con la anterior (fichero mas pequeno)
            flat = list(q[0]) + [v for k in range(1, len(q)) for v in (q[k][0] - q[k-1][0], q[k][1] - q[k-1][1])]
            edges.append([a, b, round(length, 1), flat])
            start, coords, length = i, [p], 0.0

json.dump({"n": nodes, "e": edges}, open(out, "w"), separators=(",", ":"))
print(len(ways), "caminos ->", len(nodes), "vertices,", len(edges), "tramos")
