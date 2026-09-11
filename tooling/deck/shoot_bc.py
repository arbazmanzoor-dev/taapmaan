"""Retake only the deck's broadcast-composer shot (Gujarati, outdoor workers, May peak).
Headless Chrome, throwaway profile. Opens the composer, never presses Send.

usage: deck/bin/python shoot_bc.py <scratchpad> [base_url]
"""
import subprocess, json, time, base64, urllib.request, os, sys, shutil
import websocket
from PIL import Image

P = sys.argv[1]; BASE = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8001"
OUT = f"{P}/shots"; os.makedirs(OUT, exist_ok=True)
PROF = f"{P}/chrome-prof-bc"; shutil.rmtree(PROF, ignore_errors=True)
CH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"; PORT = 9334
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
    def rect(sel):
        return js(f"(()=>{{const e=document.querySelector({json.dumps(sel)}); if(!e) return null; const r=e.getBoundingClientRect(); return [r.left,r.top,r.right,r.bottom]}})()")
    def save(img, box, name, pad=10):
        l, t, r, b = box
        im = img.crop((max(0, int((l - pad) * DPR)), max(0, int((t - pad) * DPR)), int((r + pad) * DPR), int((b + pad) * DPR)))
        im.save(f"{OUT}/{name}.jpg", quality=90); print(f"  {name}.jpg  {im.width}x{im.height}")

    cmd("Page.enable"); cmd("Runtime.enable")
    cmd("Emulation.setEmulatedMedia", features=[{"name": "prefers-color-scheme", "value": "light"}])
    metrics(1000)
    cmd("Page.navigate", url=BASE + "/")
    wait("typeof S!=='undefined' && API.base && document.querySelectorAll('#mapSvg .hex').length===37", 40)
    time.sleep(1.0)
    js("document.querySelector('.seg-b[data-mode=\"scenario\"]').click()")
    wait("!S.server && document.getElementById('srcTxt').textContent.includes('MAY PEAK')", 15); time.sleep(1.5)
    metrics(1000); js("window.scrollTo(0,0)")
    js("document.getElementById('pushBtn').click()"); time.sleep(0.5)
    js("document.querySelectorAll('#langOpts .opt')[2].click()"); time.sleep(0.4)
    js("document.querySelectorAll('#audOpts .opt')[1].click()")
    js("Promise.resolve(S.pvP).then(()=>true)"); time.sleep(0.5)       # server preview has landed
    print("  composer:", js("document.getElementById('mChars').textContent + ' | ' + document.getElementById('mRecip').textContent"))
    save(snap(), rect(".modal"), "broadcast_gujarati", pad=2)
finally:
    proc.terminate()
    try: proc.wait(5)
    except subprocess.TimeoutExpired: proc.kill()
    shutil.rmtree(PROF, ignore_errors=True)
