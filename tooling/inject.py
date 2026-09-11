"""Inject ward centres and Leaflet's stylesheet into heatguard.html between their
markers, then rebuild index.html and extract the script for a syntax check.

usage: python inject.py <project_dir> <scratchpad_dir>
"""
import json, pathlib, re, sys

D, SP = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
hg_p = D / "heatguard.html"
hg = hg_p.read_text(encoding="utf-8")

geo = json.loads((D / "backend" / "data" / "ward_geo.json").read_text(encoding="utf-8"))
compact = {c: {n: {"lat": g["lat"], "lon": g["lon"], "source": g["source"]}
               for n, g in ws.items() if g.get("lat") is not None}
           for c, ws in geo.items()}
js = json.dumps(compact, ensure_ascii=False, separators=(",", ":"))
hg, n1 = re.subn(r"/\*WARD_GEO\*/.*?/\*END_WARD_GEO\*/",
                 lambda m: "/*WARD_GEO*/" + js + "/*END_WARD_GEO*/", hg, flags=re.S)

css = (SP / "leaflet.min.css").read_text(encoding="utf-8")
css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)      # no comments: they could close the marker early
hg, n2 = re.subn(r"/\*LEAFLET_CSS\*/.*?/\*END_LEAFLET_CSS\*/",
                 lambda m: "/*LEAFLET_CSS*/" + css + "/*END_LEAFLET_CSS*/", hg, flags=re.S)
assert n1 == 1 and n2 == 1, f"markers found: ward_geo={n1} leaflet_css={n2}"
hg_p.write_text(hg, encoding="utf-8")

pre = (SP / "index_prefix.txt").read_text(encoding="utf-8")
post = (SP / "index_suffix.txt").read_text(encoding="utf-8")
(D / "index.html").write_text(pre + hg + post, encoding="utf-8")
(SP / "hg_check.js").write_text("\n".join(re.findall(r"<script>(.*?)</script>", hg, re.S)), encoding="utf-8")
print("wards with a position:", {c: len(v) for c, v in compact.items()},
      f"| leaflet css {len(css)} chars | page {len(hg)} chars")
