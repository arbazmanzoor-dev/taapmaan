"""Printable daily heat bulletin -- the document a HAP nodal officer signs.

A4, typeset in the Taapmaan design system, but still no logos or seals. It is
marked DRAFT until a named officer signs it, because a machine-generated page
must never be mistaken for an issued government order.
"""
from __future__ import annotations
import datetime as dt
from html import escape as e

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))

def _ist(iso: str) -> str:
    try:
        return dt.datetime.fromisoformat(iso).astimezone(IST).strftime("%d %b %H:%M IST")
    except (TypeError, ValueError):
        return iso or "—"

# solid, wash, ink -- the dashboard's 5-level heat-risk scale
BAND_HEX = {"GREEN": "#15803D", "YELLOW": "#B45309", "ORANGE": "#EA580C", "RED": "#DC2626", "MAGENTA": "#9333EA"}
BAND_WASH = {"GREEN": "#F0FDF4", "YELLOW": "#FEF3C7", "ORANGE": "#FFEDD5", "RED": "#FEF2F2", "MAGENTA": "#FAF5FF"}
BAND_INK = {"GREEN": "#166534", "YELLOW": "#92400E", "ORANGE": "#9A3412", "RED": "#991B1B", "MAGENTA": "#6B21A8"}
STATUS_TXT = {"pending": "Pending", "acknowledged": "Acknowledged",
              "in_progress": "In progress", "done": "Done"}

def _n(x, d=1):
    return "—" if x is None else f"{x:,.{d}f}"

def _chip(code: str, label: str) -> str:
    return (f"<span class='lv' style='background:{BAND_WASH.get(code, '#F4F0EA')};color:{BAND_INK.get(code, '#1C1917')};"
            f"border-color:{BAND_HEX.get(code, '#57534E')}'>{e(code)} · {e(label)}</span>")

def render(c: dict) -> str:
    lv = c["level"]
    col, wash, ink = (BAND_HEX.get(lv["code"], "#57534E"), BAND_WASH.get(lv["code"], "#F4F0EA"),
                      BAND_INK.get(lv["code"], "#1C1917"))
    drill = c["drill"]

    days = "".join(
        f"<tr><td class='m'>{e(d['date'])}</td><td>{_chip(d['code'], d['label'])}</td>"
        f"<td class='n'>{_n(d['htsi'])}</td><td class='n'>{_n(d['tmax_c'])}</td><td class='n'>{_n(d['tmin_c'])}</td>"
        f"<td class='n'>{d['wards_over_threshold']}</td><td class='n'>{_n(d['excess_deaths'])}</td></tr>"
        for d in c["timeline"])

    wards = "".join(
        f"<tr><td class='m'>{e(w['code'])}</td><td><b>{e(w['name'])}</b></td><td>{_chip(w['band'], w['label'])}</td>"
        f"<td class='n'>{_n(w['htsi'])}</td><td class='n'>{_n(w['wbgt'])}</td><td class='n'>{_n(w['tmin'])}</td>"
        f"<td class='n'>{w['pop']:,}</td><td class='n'>{w['cooling']}</td></tr>"
        for w in c["wards"])

    acts = "".join(
        f"<tr><td>{e(a['department_name'])}</td><td>{e(a['title'])}</td><td>{e(a['owner'])}</td>"
        f"<td>{e(STATUS_TXT.get(a['status'], a['status']))}{' — <b class=late>OVERDUE</b>' if a.get('overdue') else ''}</td>"
        f"<td class='n'>{e(_ist(a['due_at']))}</td></tr>"
        for a in c["actions"]) or "<tr><td colspan='5'>No actions active at this level.</td></tr>"

    adv = "".join(f"<div class='adv'><div class='lbl'>{e(lang)}</div><pre>{e(txt)}</pre></div>"
                  for lang, txt in c["advisories"])

    clim = c.get("climatology") or {}
    clim_row = (f"<tr><th>Vs climate normal</th><td>{_n(clim.get('anomaly_vs_normal_c'))} °C "
                f"({e(clim.get('band',''))}; normal {_n(clim.get('normal_p50'))} °C for this date)</td></tr>"
                if clim.get("available") else "")

    s = c["summary"]
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>{e(c['bulletin_no'])} · Heat bulletin</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600..800&family=Inter:wght@400;500;600;700&family=Space+Mono:wght@400;700&display=swap">
<style>
@page {{ size: A4; margin: 12mm; }}
* {{ box-sizing: border-box; }}
:root {{ --line:#E6E2DA; --sub:#FAF8F5; --ink:#1C1917; --ink2:#57534E; --ink3:#78716C;
  --mono:'Space Mono', ui-monospace, Menlo, monospace; --disp:'Bricolage Grotesque', 'Inter', sans-serif; }}
body {{ font: 9.8pt/1.45 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif; color:var(--ink); margin:0; background:#F4F0EA; }}
.bar {{ position:sticky; top:0; display:flex; align-items:center; gap:12px; justify-content:space-between;
  background:#1C1917; color:#FAF8F5; padding:10px 18px; font-size:10pt; }}
.bar button {{ font:600 10pt 'Inter', sans-serif; padding:7px 14px; border:0; background:#FAF8F5; color:#1C1917; border-radius:6px; cursor:pointer; }}
.page {{ max-width: 194mm; margin: 8mm auto; padding: 12mm; background:#fff; border:1px solid var(--line);
  box-shadow: 0 4px 6px -1px rgba(28,25,23,.05), 0 12px 28px -6px rgba(28,25,23,.1); }}
header {{ border-bottom: 2px solid var(--ink); padding-bottom: 8px; display:flex; justify-content:space-between; gap:16px; align-items:flex-end; }}
h1 {{ font: 700 17pt/1.1 var(--disp); letter-spacing:-.01em; margin: 0; }}
.sub {{ color:var(--ink2); font-size:9pt; margin-top:3px; }}
.meta {{ font: 8.3pt/1.6 var(--mono); border:1px solid var(--line); border-radius:6px; padding:6px 10px; background:var(--sub); white-space:nowrap; }}
.draft {{ margin:9px 0 0; padding:7px 11px; border:1px solid #FECACA; border-left:3px solid #DC2626; background:#FEF2F2;
  color:#991B1B; font-weight:600; font-size:9pt; border-radius:4px; }}
.drill {{ margin:9px 0 0; padding:8px 11px; background:#1C1917; color:#fff; font: 700 9pt var(--mono); letter-spacing:.04em; border-radius:4px; }}
.level {{ margin: 12px 0 2px; display:flex; align-items:center; gap:14px; border:1.5px solid {col}; background:{wash}; border-radius:8px; padding:10px 12px; }}
.level .badge {{ background:{col}; color:#fff; border-radius:6px; padding:8px 14px; min-width:56mm;
  font: 700 7.5pt var(--mono); letter-spacing:.08em; text-transform:uppercase; }}
.level .badge b {{ display:block; font: 700 16pt/1.1 var(--disp); letter-spacing:-.01em; text-transform:none; margin-top:2px; }}
.level p {{ margin:0; color:{ink}; font-size:9.3pt; }}
h2 {{ font: 700 10.5pt var(--disp); margin: 15px 0 6px; display:flex; align-items:center; gap:7px; text-transform:uppercase; letter-spacing:.02em; }}
h2 i {{ font: 700 7.5pt var(--mono); font-style:normal; width:16px; height:16px; display:grid; place-items:center; background:var(--ink); color:#fff; border-radius:3px; }}
.metrics {{ display:grid; grid-template-columns: repeat(4, 1fr); gap:6px; margin-bottom:6px; }}
.metrics div {{ border:1px solid var(--line); border-radius:6px; padding:6px 9px; }}
.metrics span {{ display:block; font: 700 6.8pt var(--mono); letter-spacing:.06em; text-transform:uppercase; color:var(--ink3); }}
.metrics b {{ font: 700 13pt var(--mono); letter-spacing:-.02em; }}
.metrics small {{ display:block; font-size:8pt; color:var(--ink2); }}
table {{ width:100%; border-collapse:collapse; font-size:8.8pt; border:1px solid var(--line); }}
th, td {{ text-align:left; padding:4px 7px; border-bottom:1px solid var(--line); vertical-align:top; }}
thead th {{ background:var(--sub); font: 700 7.2pt var(--mono); letter-spacing:.05em; text-transform:uppercase; color:var(--ink2); }}
td.n, th.n {{ text-align:right; font: 8.3pt var(--mono); white-space:nowrap; }}
td.m {{ font: 8.3pt var(--mono); white-space:nowrap; }}
.kv th {{ width:52mm; font-weight:500; color:var(--ink2); background:var(--sub); }}
.lv {{ display:inline-block; font: 700 7pt var(--mono); letter-spacing:.04em; text-transform:uppercase; padding:1px 6px; border-radius:4px; border:1px solid; white-space:nowrap; }}
.late {{ color:#DC2626; }}
.advs {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(55mm, 1fr)); gap:6px; }}
.adv {{ border:1px solid var(--line); border-radius:6px; padding:7px 9px; }}
.adv pre {{ margin:4px 0 0; white-space:pre-wrap; font: 8.8pt/1.45 'Inter', sans-serif; }}
.lbl {{ font: 700 7.2pt var(--mono); text-transform:uppercase; letter-spacing:.07em; color:var(--ink2); }}
.note {{ font-size:8.3pt; color:var(--ink2); }}
.sign {{ display:grid; grid-template-columns: 1fr 1fr 1fr; gap: 6mm; margin-top: 10mm; }}
.sign div {{ border:1px solid var(--line); border-radius:6px; padding:8px 10px 9px; min-height:26mm; display:flex; flex-direction:column; font-size:8.5pt; }}
.sign div span {{ font: 700 7.2pt var(--mono); text-transform:uppercase; letter-spacing:.05em; color:var(--ink2); }}
.sign div i {{ margin-top:auto; border-top:1px solid var(--ink); padding-top:3px; font-style:normal; color:var(--ink3); }}
.sign .nodal {{ border:1.5px solid var(--ink); }}
footer {{ margin-top: 8mm; border-top:1px solid var(--line); padding-top:5px; font-size:7.8pt; color:var(--ink3); }}
section {{ break-inside: avoid; }}
@media print {{ body {{ background:#fff; }} .bar {{ display:none; }} .page {{ margin:0; padding:0; border:0; box-shadow:none; max-width:none; }} }}
</style></head><body>
<div class="bar"><span><b>Daily heat bulletin</b> · A4 print preview</span><button onclick="window.print()">Print / save as PDF</button></div>
<div class="page">
<header>
  <div><h1>{e(c['corp'])} · Daily Heat Bulletin</h1>
  <div class="sub">Heat Action Plan · {e(c['census_unit'])} · {e(c['city'])}</div></div>
  <div class="meta">No. <b>{e(c['bulletin_no'])}</b><br>Generated {e(c['issued_at'])}<br>Valid for <b>{e(c['valid_for'])}</b></div>
</header>
{"<div class='drill'>DRILL — MAY PEAK SCENARIO. NOT A REAL FORECAST. DO NOT CIRCULATE AS AN ALERT.</div>" if drill else ""}
<div class="draft">DRAFT — machine-generated by Taapmaan. Not valid until reviewed and signed by the Heat Action Plan Nodal Officer.</div>

<section class="level"><div class="badge">Operating level<b>{e(lv['code'])} · {e(lv['name'])}</b></div>
<p>Set from the peak city Human Thermal Stress Index over the next 72 hours
(HTSI {_n(lv['htsi'])}, peak on day +{lv['peak_day']}). Departments act on this level, before the peak arrives.</p></section>

<section><h2><i>1</i>Situation — day +{c['horizon']}</h2>
<div class="metrics">
  <div><span>City stress index</span><b>{_n(s['htsi'])}</b> / 100<small>{e(s['label'])}</small></div>
  <div><span>Peak WBGT</span><b>{_n(s['peak_wbgt_c'])} °C</b></div>
  <div><span>Peak UTCI</span><b>{_n(s['peak_utci_c'])} °C</b></div>
  <div><span>Wards severe or worse</span><b>{s['wards_over_threshold']} / {c['n_wards']}</b><small>{s['population_exposed']:,} people</small></div>
</div>
<table class="kv">
{clim_row}
<tr><th>Modelled health load, 24 h</th><td>{_n(s['excess_deaths'])} excess deaths · {s['ed_presentations']:,} emergency presentations · {s['ambulance_calls']:,} 108 calls</td></tr>
</table></section>

<section><h2><i>2</i>Five-day outlook</h2>
<table><thead><tr><th>Date</th><th>Level</th><th class="n">HTSI</th><th class="n">Max °C</th><th class="n">Night min °C</th><th class="n">Severe wards</th><th class="n">Excess deaths</th></tr></thead>
<tbody>{days}</tbody></table></section>

<section><h2><i>3</i>Highest-risk wards</h2>
<table><thead><tr><th>Code</th><th>Ward</th><th>Level</th><th class="n">HTSI</th><th class="n">WBGT °C</th><th class="n">Night min °C</th><th class="n">Population</th><th class="n">Cooling centres</th></tr></thead>
<tbody>{wards}</tbody></table></section>

<section><h2><i>4</i>Department actions</h2>
<table><thead><tr><th>Department</th><th>Action</th><th>Owner</th><th>Status</th><th class="n">Due</th></tr></thead>
<tbody>{acts}</tbody></table>
<p class="note">{e(c['sop_caveat'])}</p></section>

<section><h2><i>5</i>Public advisory</h2><div class="advs">{adv}</div>
{f"<p class='note'>{e(c['lang_note'])}</p>" if c.get('lang_note') else ""}</section>

<div class="sign">
  <div><span>Prepared by (control room)</span><i>Name, designation &amp; signature</i></div>
  <div class="nodal"><span>HAP Nodal Officer — approval</span><i>Name, designation &amp; signature</i></div>
  <div><span>Date &amp; time of issue</span><i>DD / MM / YYYY · HH:MM IST</i></div>
</div>

<footer>Weather: {e(c['weather_source'])}. Demography: Census of India 2011 city tables; ward splits partly modelled. Capacity figures (beds, cooling centres) are modelled
and must be replaced with the municipal register. Mortality figures are a parametric exposure–response estimate, not a fitted model.
Taapmaan decision support — the issuing officer remains responsible for the content of this bulletin.</footer>
</div></body></html>"""
