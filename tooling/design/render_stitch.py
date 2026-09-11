"""Render Stitch HTML exports to full-page PNGs with headless Chrome (throwaway profile).

usage: deck/bin/python render_stitch.py <stitch_dir> <out_dir> name[:width] ...
"""
import subprocess, json, time, base64, urllib.request, os, sys, shutil, pathlib
import websocket

SRC, OUT = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
JOBS = [(a.split(":")[0], int(a.split(":")[1]) if ":" in a else 1440) for a in sys.argv[3:]]
PROF = str(OUT / "_prof"); shutil.rmtree(PROF, ignore_errors=True)
CH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"; PORT = 9335
proc = subprocess.Popen([CH, "--headless=new", f"--remote-debugging-port={PORT}", "--remote-allow-origins=*",
    f"--user-data-dir={PROF}", "--no-first-run", "--no-default-browser-check", "--hide-scrollbars",
    "--force-color-profile=srgb", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
    def js(e): return cmd("Runtime.evaluate", expression=e, returnByValue=True)["result"].get("value")
    cmd("Page.enable"); cmd("Runtime.enable")
    cmd("Emulation.setEmulatedMedia", features=[{"name": "prefers-color-scheme", "value": "light"}])
    for name, w in JOBS:
        f = SRC / f"{name}.html"
        cmd("Emulation.setDeviceMetricsOverride", width=w, height=900, deviceScaleFactor=1, mobile=w < 600)
        cmd("Page.navigate", url=f.resolve().as_uri()); time.sleep(4.5)       # Tailwind CDN + fonts
        h = min(int(js("Math.ceil(document.documentElement.scrollHeight)") or 900), 6000)
        cmd("Emulation.setDeviceMetricsOverride", width=w, height=h, deviceScaleFactor=1, mobile=w < 600); time.sleep(1.2)
        png = base64.b64decode(cmd("Page.captureScreenshot", format="png")["data"])
        (OUT / f"{name}.png").write_bytes(png); print(f"  {name}.png  {w}x{h}")
finally:
    proc.terminate()
    try: proc.wait(5)
    except subprocess.TimeoutExpired: proc.kill()
    shutil.rmtree(PROF, ignore_errors=True)
