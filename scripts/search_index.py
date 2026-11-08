"""Indice de busqueda compacto para el visor: [nombre, tipo, altitud|null, lon, lat] por elemento."""
import json, sys

src, out = sys.argv[1], sys.argv[2]
feats = json.load(open(src, encoding="utf-8"))["features"]
rows, seen = [], set()
for f in feats:
    p, g = f["properties"], f["geometry"]
    name = (p.get("name") or "").strip()
    if not name: continue
    c = g["coordinates"]
    lon, lat = c if g["type"] == "Point" else c[len(c) // 2]
    key = (name, p["kind"], round(lon, 2), round(lat, 2))
    if key in seen: continue
    seen.add(key)
    rows.append([name, p["kind"], p.get("ele"), round(lon, 5), round(lat, 5)])
json.dump(rows, open(out, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(len(rows), "entradas en el buscador")
