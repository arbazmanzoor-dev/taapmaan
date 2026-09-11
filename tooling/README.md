# tooling

Scripts that built the pitch deck, took its screenshots, embedded the street-map
data and tested the broadcast API. None of this is needed to run the app. Commands
run from the project root.

| File | What it does | How to run |
|---|---|---|
| `deck/build_deck.py` | Builds `Taapmaan_SIH_Idea_Submission.pptx` from `deck/facts.json` and `deck/shots/` | `python tooling/deck/build_deck.py tooling/deck Taapmaan_SIH_Idea_Submission.pptx` (needs `pip install python-pptx pillow lxml`) |
| `deck/shoot.py` | Screenshots every view with headless Chrome into `deck/shots/` | `python tooling/deck/shoot.py tooling/deck` (needs `pip install websocket-client pillow`; targets `localhost:8000`) |
| `deck/shoot_bc.py` | Retakes only the broadcast-composer shot | `python tooling/deck/shoot_bc.py tooling/deck http://localhost:8000` |
| `inject.py` | Embeds ward centres (`backend/data/ward_geo.json`) and Leaflet's stylesheet into `heatguard.html`, then rebuilds `index.html` | `python tooling/inject.py . tooling` |
| `test_broadcast.py` | 62 checks of the broadcast API on a throwaway database | `backend/.venv/bin/python tooling/test_broadcast.py backend /tmp/taapmaan-test` |
| `design/stitch/` | The Stitch design exports (HTML, screenshots, `design.md`) the UI was ported from | reference only |
| `design/render_stitch.py` | Renders Stitch HTML exports to full-size PNGs | `python tooling/design/render_stitch.py tooling/design/stitch tooling/design/stitch/render <screen>` |

**Careful with `shoot.py`:** its command-centre step moves drill actions forward,
which writes drill records to whichever server it points at. Run it against a
throwaway copy, for example:

```bash
cd backend && TAAPMAAN_DB=/tmp/shots.db ./.venv/bin/python -m uvicorn app.main:app --port 8001
```

then point the script at port 8001.

**Ward centres:** `backend/scripts/geocode_wards.py` fills in wards OpenStreetMap
has not located yet (Delhi and most of Lucknow were rate-limited on the first run).
Rerun it, then `inject.py`, to put the new positions on the street map.
