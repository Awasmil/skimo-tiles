"""Zona de trabajo del mapa (donde hay relieve propio del IGN): poligono(s) en GeoJSON WGS84,
generado en pages.yml a partir de las hojas MDT02. Funciones para filtrar puntos y recortar lineas."""
import json


def load_coverage(path):
    """Devuelve lista de poligonos; cada poligono = lista de anillos [(lon, lat), ...] (exterior + huecos)."""
    gj = json.load(open(path, encoding="utf-8"))
    polys = []
    for f in gj.get("features", []):
        g = f.get("geometry") or {}
        if g.get("type") == "Polygon":
            polys.append(g["coordinates"])
        elif g.get("type") == "MultiPolygon":
            polys.extend(g["coordinates"])
    # caja de cada poligono para descartar rapido
    return [(p, (min(x for x, _ in p[0]), min(y for _, y in p[0]), max(x for x, _ in p[0]), max(y for _, y in p[0]))) for p in polys]


def _in_rings(rings, x, y):
    c = False   # par-impar sobre todos los anillos: los huecos quedan fuera
    for ring in rings:
        n = len(ring)
        for i in range(n):
            x1, y1 = ring[i][0], ring[i][1]
            x2, y2 = ring[(i + 1) % n][0], ring[(i + 1) % n][1]
            if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                c = not c
    return c


def inside(cov, x, y):
    return any(b[0] <= x <= b[2] and b[1] <= y <= b[3] and _in_rings(p, x, y) for p, b in cov)


def clip_line(cov, coords):
    """Trozos de la linea con los vertices dentro de la zona (al menos 2 puntos)."""
    parts, cur = [], []
    for c in coords:
        if inside(cov, c[0], c[1]):
            cur.append(c)
        else:
            if len(cur) >= 2: parts.append(cur)
            cur = []
    if len(cur) >= 2: parts.append(cur)
    return parts
