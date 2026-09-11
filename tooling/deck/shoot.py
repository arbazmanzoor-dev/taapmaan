"""Screenshot the running Taapmaan dashboard via headless Chrome + DevTools protocol.
Isolated throwaway profile; never touches the user's Chrome."""
import subprocess, json, time, base64, urllib.request, os, sys, shutil
import websocket
from PIL import Image

P = sys.argv[1]; OUT = f"{P}/shots"; os.makedirs(OUT, exist_ok=True)
PROF = f"{P}/chrome-prof"; shutil.rmtree(PROF, ignore_errors=True)
CH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"; PORT = 9333
proc = subprocess.Popen([CH, "--headless=new", f"--remote-debugging-port={PORT}", "--remote-allow-origins=*",
    f"--user-data-dir={PROF}", "--no-first-run", "--no-default-browser-check", "--hide-scrollbars",
    "--force-color-profile=srgb", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
W, DPR = 1600, 2
try:
    for _ in range(100):
        try: urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version", timeout=1); break
        except Exception: time.sleep(0.2)
    pg = [t for t in json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json")) if t["type"] == "page"][0]
    ws = websocket.create_connection(pg["webSocketDebuggerUrl"], timeout=90, suppress_origin=True)
    N = [0]
    def cmd(method, **params):
        N[0] += 1; i = N[0]; ws.send(json.dumps({"id": i, "method": method, "params": params}))
        while True:
            m = json.loads(ws.recv())
            if m.get("id") == i:
                if "error" in m: raise RuntimeError(f"{method}: {m['error']}")
                return m.get("result", {})
    def js(expr):
        r = cmd("Runtime.evaluate", expression=expr, awaitPromise=True, returnByValue=True)
        if r.get("exceptionDetails"): raise RuntimeError("JS: " + json.dumps(r["exceptionDetails"])[:300])
        return r["result"].get("value")
    def wait(cond, timeout=25):
        t = time.time()
        while time.time() - t < timeout:
            try:
                if js(f"!!({cond})"): return
            except Exception: pass
            time.sleep(0.25)
        raise RuntimeError("timeout: " + cond)
    def metrics(h, w=W): cmd("Emulation.setDeviceMetricsOverride", width=w, height=h, deviceScaleFactor=DPR, mobile=False)
    def snap():
        r = cmd("Page.captureScreenshot", format="png"); fn = f"{OUT}/_raw.png"
        open(fn, "wb").write(base64.b64decode(r["data"])); return Image.open(fn).convert("RGB")
    def full(w=W):
        h = js("Math.ceil(document.documentElement.scrollHeight)"); metrics(max(h, 800), w); time.sleep(0.9); return snap()
    def rect(sel):
        return js(f"(()=>{{const e=document.querySelector({json.dumps(sel)}); if(!e) return null; const r=e.getBoundingClientRect(); return [r.left,r.top,r.right,r.bottom]}})()")
    def union(*sels):
        rs = [r for r in (rect(s) for s in sels) if r]
        return [min(r[0] for r in rs), min(r[1] for r in rs), max(r[2] for r in rs), max(r[3] for r in rs)]
    def save(img, box, name, pad=10):
        l, t, r, b = box
        im = img.crop((max(0, int((l - pad) * DPR)), max(0, int((t - pad) * DPR)), int((r + pad) * DPR), int((b + pad) * DPR)))
        im.save(f"{OUT}/{name}.jpg", quality=90); print(f"  {name}.jpg  {im.width}x{im.height}")

    cmd("Page.enable"); cmd("Runtime.enable")
    cmd("Emulation.setEmulatedMedia", features=[{"name": "prefers-color-scheme", "value": "light"}])
    metrics(1000)
    cmd("Page.navigate", url="http://localhost:8000/")
    wait("typeof S!=='undefined' && S.server && S.server.ml && document.querySelectorAll('#mapSvg .hex').length===37", 40)
    time.sleep(1.5)

    # 1) LIVE: forecast strip + learned-forecast panel (only meaningful with the backend)
    img = full(); save(img, rect("#secForecast > .panel"), "live_forecast_ml")
    save(img, union("#secSources"), "live_pipeline_api")

    # 2) MAY PEAK scenario: the dramatic map + ward dossier
    metrics(1000); js("window.scrollTo(0,0)")
    js("document.querySelector('.seg-b[data-mode=\"scenario\"]').click()")
    wait("!S.server && document.getElementById('srcTxt').textContent.includes('MAY PEAK')", 15); time.sleep(1.5)
    snap().save(f"{OUT}/hero_scenario.jpg", quality=90); print("  hero_scenario.jpg  viewport 1600x1000 @2x")
    img = full()
    save(img, union("#secOverview"), "scenario_map_alerts")
    save(img, rect("#wardPanel"), "scenario_ward_panel", pad=4)

    # 3) Broadcast composer in Gujarati
    metrics(1000); js("window.scrollTo(0,0)")
    js("document.getElementById('pushBtn').click()"); time.sleep(0.5)
    js("document.querySelectorAll('#langOpts .opt')[2].click()"); time.sleep(0.4)
    js("document.querySelectorAll('#audOpts .opt')[1].click()"); time.sleep(0.4)
    save(snap(), rect(".modal"), "broadcast_gujarati", pad=2)
    js("document.getElementById('mClose').click()"); time.sleep(0.3)

    # 4) Command centre, drill mode, with a board mid-way through a drill
    js("""(async()=>{
      await fetch('/v1/command?city=ahmedabad&mode=scenario');
      const set=(id,st)=>fetch('/v1/command/action',{method:'POST',headers:{'content-type':'application/json'},
        body:JSON.stringify({city:'ahmedabad',mode:'scenario',action_id:id,status:st,actor:'Control room'})});
      for (const [id,st] of [['dm-bulletin','done'],['in-advisory','done'],['dm-eoc','done'],['dm-meeting','in_progress'],
                             ['hl-rooms','in_progress'],['hl-stock','acknowledged'],['mu-cooling','acknowledged'],
                             ['lb-suspend','acknowledged'],['pw-outage','in_progress']]) await set(id,st);
      return true;})()""")
    js("document.getElementById('opName').value='Control room'")
    js("setView('command')"); wait("CMD.data && document.querySelectorAll('.act').length>5", 20); time.sleep(1.0)
    js("window.scrollTo(0,0)")
    img = full(); save(img, union("#drillBanner", "#cmdHead", "#cmdGrid"), "command_centre_drill")
    save(img, union("#cmdHead"), "command_head", pad=4)

    # 5) Printable bulletin (drill)
    metrics(1000, 980)
    cmd("Page.navigate", url="http://localhost:8000/bulletin?city=ahmedabad&horizon=3&mode=scenario")
    wait("document.querySelector('.page') && document.querySelectorAll('tbody tr').length>5", 20); time.sleep(0.8)
    img = full(980); l, t, r, b = rect(".page"); ht = rect("header")[1]; save(img, [l, ht, r, min(b, ht + 1180)], "bulletin_top", pad=14)

    # 6) Auto-generated API docs
    metrics(1000, 1440)
    cmd("Page.navigate", url="http://localhost:8000/docs")
    try:
        wait("document.querySelectorAll('.opblock').length>10", 25); time.sleep(1.0)
        save(snap(), [0, 0, 1440, 1000], "api_docs", pad=0)
    except RuntimeError as e:
        print("  api_docs skipped:", e)
finally:
    proc.terminate()
    try: proc.wait(5)
    except Exception: proc.kill()
    shutil.rmtree(PROF, ignore_errors=True)
print("done ->", OUT)
