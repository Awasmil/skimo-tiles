"""Indice del buscador con TODO lo que tiene nombre en OpenStreetMap (picos, rios, lagos, caminos, pistas,
collados, bosques, ermitas, pueblos...). Salida: [[nombre, tipo, altitud|null, lon, lat], ...]
Uso: python3 search_all.py S,W,N,E salida.json"""
import json, sys, time, urllib.parse, urllib.request

bbox, out = sys.argv[1], sys.argv[2]
URLS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]

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

# Tipo en castellano segun la etiqueta principal (el orden importa: lo mas especifico primero)
KINDS = [
    ("natural", {"peak": "peak", "saddle": "saddle", "spring": "spring", "water": "lake", "glacier": "Glaciar", "cliff": "Cortado",
                 "ridge": "Cresta", "arete": "Arista", "valley": "Valle", "cave_entrance": "Cueva", "wood": "Bosque",
                 "scree": "Pedrera", "bare_rock": "Roca", "grassland": "Prado", "heath": "Landa", "wetland": "Humedal", "rock": "Roca"}),
    ("mountain_pass", {"yes": "saddle"}),
    ("tourism", {"alpine_hut": "hut", "wilderness_hut": "unguarded_hut", "viewpoint": "Mirador", "camp_site": "Camping",
                 "hotel": "Hotel", "information": "Información", "attraction": "Lugar de interés"}),
    ("amenity", {"shelter": "shelter", "place_of_worship": "Iglesia / ermita", "parking": "Aparcamiento", "drinking_water": "spring",
                 "restaurant": "Restaurante", "bar": "Bar"}),
    ("waterway", {"river": "river", "stream": "stream", "waterfall": "Cascada", "dam": "Presa", "canal": "Canal"}),
    ("piste:type", {"downhill": "Pista de esquí", "nordic": "Pista de fondo", "skitour": "Itinerario de esquí de montaña"}),
    ("aerialway", {None: "Remonte"}),
    ("highway", {"path": "Sendero", "footway": "Sendero", "track": "Pista forestal", "bridleway": "Camino", "steps": "Escaleras",
                 None: "Carretera / calle"}),
    ("route", {"hiking": "Ruta de senderismo", "foot": "Ruta de senderismo", "ski": "Ruta de esquí", "piste": "Ruta de esquí", "road": "Carretera"}),
    ("place", {"town": "place", "village": "place", "hamlet": "place", "locality": "place", "isolated_dwelling": "place", None: "place"}),
    ("historic", {None: "Patrimonio"}),
    ("landuse", {"forest": "Bosque", "meadow": "Prado", "winter_sports": "Estación de esquí", None: None}),
    ("leisure", {None: "Ocio"}),
    ("man_made", {None: "Construcción"}),
    ("building", {None: "Edificio"}),
]
def kind(t):
    for key, m in KINDS:
        if key in t:
            k = m.get(t[key], m.get(None, "Lugar"))
            if k: return k
    return "Lugar"

def ele(t):
    try: return round(float(str(t.get("ele", "")).replace(",", ".").split()[0]))
    except (ValueError, IndexError): return None

els = overpass(f'[out:json][timeout:240];nwr["name"]({bbox});out center tags;')
rows, seen = [], set()
for e in els:
    t = e.get("tags", {}); name = t.get("name", "").strip()
    if not name: continue
    c = (e["lon"], e["lat"]) if "lon" in e else (e.get("center", {}).get("lon"), e.get("center", {}).get("lat"))
    if c[0] is None: continue
    k = kind(t)
    key = (name, k, round(c[0], 2), round(c[1], 2))
    if key in seen: continue
    seen.add(key)
    rows.append([name, k, ele(t), round(c[0], 5), round(c[1], 5)])
json.dump(rows, open(out, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(len(rows), "elementos con nombre en el buscador")
