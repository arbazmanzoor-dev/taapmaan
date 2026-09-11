# Deploying Taapmaan — step by step

You will end with a public link like `https://taapmaan.onrender.com` that anyone can
open. It takes about 20 minutes, costs nothing, and needs two free accounts:
**GitHub** (stores the code) and **Render** (runs it).

---

## What you have

| File / folder | What it is |
|---|---|
| `taapmaan-deploy.zip` | Everything Render needs: backend, dashboard, data, ML models, deploy files. No passwords, no database. |
| `DEPLOY.md` | This guide. |
| `Taapmaan_SIH_Idea_Submission.pptx` / `.pdf` | The pitch deck (not deployed). |
| `~/Documents/taapmaan/` | The full project on your Mac, including your local database (`backend/data/taapmaan.db`). |

The deploy files inside the zip, so you know what they do:

- `Dockerfile` — how Render builds and starts the app.
- `render.yaml` — the Render "Blueprint": one free web service, a health check, and two
  secrets Render generates for you (`TAAPMAAN_SALT`, `TAAPMAAN_OPERATOR_TOKEN`).

---

## Stage 1 — Put the code on GitHub (5 min)

Pick **one** of the two ways.

### Way A: in the browser (no terminal)

1. Unzip `taapmaan-deploy.zip`. You get a folder called `taapmaan-deploy`.
2. Go to **github.com** and sign in (or **Sign up**, free).
3. Top right **+** → **New repository**.
   - Repository name: `taapmaan`
   - **Private** (only you see the code) or **Public** (judges can read it). Either works with Render.
   - Leave "Add a README" **unticked**.
   - **Create repository**.
4. On the empty repository page, click the link **uploading an existing file**.
5. Open the `taapmaan-deploy` folder in Finder, select **everything inside it**
   (Cmd + A), and drag it onto the GitHub page. Use Chrome if Safari will not take folders.
   Wait until every file is listed (about 90 files).
6. Scroll down, click **Commit changes**.
7. Check the repository page shows `Dockerfile`, `render.yaml`, `backend`, `index.html`
   at the top level (not inside another folder). If they are inside a folder, delete
   the repository (Settings → bottom of page) and repeat step 5 dragging the folder's
   *contents*, not the folder.

### Way B: with the terminal

```bash
cd ~/Documents/taapmaan
gh auth login
```

Choose **GitHub.com → HTTPS → Yes → Login with a web browser**, copy the 8-letter code,
paste it in the browser page that opens, approve. Then:

```bash
gh repo create taapmaan --private --source=. --push
```

(Use `--public` instead of `--private` if you want judges to read the code.)

---

## Stage 2 — Deploy on Render (10 min, mostly waiting)

1. Go to **render.com** → **Get Started** → **GitHub** (sign in with the same GitHub account).
   Allow Render to access your repositories (you can limit it to `taapmaan`).
2. In the Render dashboard: **New +** → **Blueprint**.
3. Pick the `taapmaan` repository → **Connect**.
4. Render reads `render.yaml` and shows one web service called **taapmaan**.
   - If it asks for `GOOGLE_MAPS_API_KEY`: leave it **empty** for now (the street map then
     uses OpenStreetMap). You can add a key later — see Stage 4.
   - Click **Apply** / **Deploy Blueprint**.
5. Wait for the first build: **5–10 minutes** (it installs the scientific libraries).
   Click the service → **Logs**. It is ready when you see
   `Application startup complete` and the status turns **Live** (green).
6. Your link is at the top of the service page, e.g. `https://taapmaan.onrender.com`
   (Render adds letters if the name is taken). Open it.

### Sign in as an official

7. Service → **Environment** → `TAAPMAAN_OPERATOR_TOKEN` → **Reveal** → copy it. It is the
   password of the five demo accounts, which the server recreates every time it starts:

   | Username | Role | Can change live records |
   |---|---|---|
   | `commissioner` | Administrator (Municipal Commissioner) | everything, and manages accounts |
   | `control.room` | Control-room operator | every department, broadcasts, bulletins |
   | `health.officer` | Department officer (Health) | Health actions only |
   | `water.officer` | Department officer (Water supply) | Water supply actions only |
   | `collector` | Viewer (District Collector) | nothing: read only |

8. On your site: **Official sign-in** (top right) → username + that password → **Sign in**.
   Your name and role appear in the header, and every live change is recorded under your name.

Visitors without an account still see everything, run **May peak** drills and send drill
dry-run broadcasts. The administrator adds more officials under **Command centre →
Officials & access**. On the free plan those extra accounts vanish when the service
restarts; the five demo accounts come back.

---

## Stage 3 — Check it works (3 min)

Open your link and tick these off:

- [ ] The dashboard loads with the Taapmaan header, sidebar and hex ward map.
- [ ] The status pill says **LIVE** (live weather) — or **NO LIVE DATA · SCENARIO** if the
      weather service is rate-limiting. Both are honest; live data returns on its own.
- [ ] **May peak** → the map turns red, the strip says "scenario — not a warning".
- [ ] **Street map** → wards appear as circles on a real map; click one for its details.
- [ ] **Broadcast alert** → **Send dry run** → the delivery log appears.
- [ ] **Command centre** (May peak) → move an action forward → it saves.
- [ ] **Print bulletin** → an A4 bulletin marked DRAFT opens in a new tab.
- [ ] `your-link/docs` → the API documentation page opens.

---

## Stage 4 (optional) — Google Maps

Without this the street map uses OpenStreetMap, which is fine for a demo.

1. **console.cloud.google.com** → sign in → create a project (e.g. "taapmaan").
2. **Billing** → link a billing account (Google requires it; normal demo use stays within the free monthly credit).
3. **APIs & Services → Library** → search **Maps JavaScript API** → **Enable**.
4. **APIs & Services → Credentials → Create credentials → API key**. Copy the key.
5. Click the key to restrict it:
   - *Application restrictions* → **Websites** → add both
     `https://YOUR-LINK.onrender.com/*` and `http://localhost:8000/*` (for testing on your Mac)
   - *API restrictions* → **Restrict key** → tick **Maps JavaScript API** → **Save**.
6. **On your Mac (optional test):** open `backend/.env`, paste the key after
   `GOOGLE_MAPS_API_KEY=`, save, restart `./run.sh`, open `http://localhost:8000` →
   **Street map**. The note under the map should say **Google Maps**.
7. **On Render:** your service → **Environment** → `GOOGLE_MAPS_API_KEY` → paste → **Save changes**.
   Render redeploys by itself (a few minutes). The map note then says **Google Maps**.

---

## Before you present

- **Open the link 2 minutes before** — the free plan sleeps after 15 minutes without
  visitors, and the first visit then takes about 30 seconds.
- **Sign in as an official** (e.g. `commissioner`) on the laptop you present from.
- **The free plan's database resets** whenever the service restarts or redeploys. Treat
  the live action history there as demo data. (Your Mac copy keeps its records.)
- Put your link in the deck: slide 6, "Repo / demo video".

---

## Updating the site later

Change code on your Mac, then:

```bash
cd ~/Documents/taapmaan
git add -A && git commit -m "describe the change" && git push
```

Render rebuilds and redeploys automatically. (If you used Way A, upload the changed
files on GitHub instead — **Add file → Upload files**.)

**Missing street-map wards** (Delhi, most of Lucknow): a few hours after the first run,

```bash
cd ~/Documents/taapmaan/backend && ./.venv/bin/python scripts/geocode_wards.py
cd .. && python3 tooling/inject.py . tooling
```

then commit and push as above.

---

## If something goes wrong

| What you see | What to do |
|---|---|
| Build fails in Render logs | Check the repository has `Dockerfile` and `render.yaml` at the top level (Stage 1, step 7). Then **Manual Deploy → Deploy latest commit**. |
| "Service Unavailable" / 502 on first visit | It is waking up. Wait 30–60 seconds and refresh. |
| **NO LIVE DATA · SCENARIO** | The free weather service is rate-limiting. The app retries every hour and labels everything as scenario meanwhile. |
| "Wrong username or password" | Usernames are lower-case (`commissioner`). The password is `TAAPMAAN_OPERATOR_TOKEN` from Render → Environment, with no spaces. Five wrong tries lock that account for 15 minutes. |
| Street map says tiles could not load | You are viewing a static copy, not the Render site. Open your onrender.com link. |
| "Google rejected the Maps key" | Stage 4, step 5: the website restriction must match your exact onrender.com address, and the Maps JavaScript API must be enabled. |
