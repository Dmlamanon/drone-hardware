"""Tessellate the STEVIE assembly STEP into triangles for shaded CDR renders.

Runs under freecadcmd, invoked by basename from this directory. NOTE:
freecadcmd puts the SCRIPT's own path in sys.argv[1], so paths are
hardcoded here rather than read from argv -- reading argv[1] makes this
script try to import itself as CAD geometry ("no supported file format").
"""
import json

import FreeCAD
import Import

BASE = r"D:\claude-obsidian\engineering\drone-hardware\mechanical\assembly-v0"
STEP = BASE + r"\stevie-assembly-v0.step"
OUT = BASE + r"\_cdr_assembly_mesh.json"

doc = FreeCAD.newDocument("cdr")
Import.insert(STEP, doc.Name)
doc.recompute()

solids = []
for obj in doc.Objects:
    shp = getattr(obj, "Shape", None)
    if shp is None or shp.isNull():
        continue
    try:
        verts, facets = shp.tessellate(0.8)
    except Exception as exc:
        print("tessellate failed for %s: %s" % (obj.Label, exc))
        continue
    if not facets:
        continue
    bb = shp.BoundBox
    solids.append({
        "label": obj.Label,
        "verts": [[round(v.x, 3), round(v.y, 3), round(v.z, 3)] for v in verts],
        "tris": [list(f) for f in facets],
        "bbox": [bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax],
        "zc": (bb.ZMin + bb.ZMax) / 2.0,
    })
    print("ok %-30s %6d tris  z=%8.1f..%8.1f" % (obj.Label, len(facets), bb.ZMin, bb.ZMax))

with open(OUT, "w") as fh:
    json.dump({"solids": solids}, fh)
print("RESULT: wrote %d solids" % len(solids))
