"""make_figures.py — renders the 7 report figures from data/*.csv and osalr/ into images/.
Run from the repository root:  python scripts/make_figures.py"""
import os, sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import matplotlib
matplotlib.use("Agg")


def apply_figure_style(sizes=(8, 7, 6)):
    """Matplotlib defaults used for every figure: open frame, outward ticks, frameless legends."""
    import matplotlib as mpl
    base, secondary, tick = sizes
    mpl.rcParams.update({
        "font.family": "sans-serif", "font.size": base, "axes.labelsize": base, "axes.titlesize": base,
        "legend.fontsize": secondary, "xtick.labelsize": tick, "ytick.labelsize": tick,
        "axes.linewidth": 0.6, "xtick.direction": "out", "ytick.direction": "out",
        "xtick.major.size": 3, "ytick.major.size": 3, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
        "axes.spines.top": False, "axes.spines.right": False, "axes.grid": False, "legend.frameon": False,
        "figure.dpi": 200, "savefig.dpi": 300, "savefig.bbox": "tight", "axes.titlelocation": "left",
        "lines.linewidth": 1.2, "patch.linewidth": 0.6, "pdf.fonttype": 42, "ps.fonttype": 42,
    })


def panel_letter(ax, letter, dx=-0.18, dy=1.02):
    import matplotlib.pyplot as plt
    ax.text(dx, dy, letter, transform=ax.transAxes, fontweight="bold",
            fontsize=plt.rcParams["font.size"] + 1, va="bottom", ha="left")

import pandas as pd, numpy as np, matplotlib as mpl, matplotlib.pyplot as plt, os, re
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
os.makedirs("images", exist_ok=True)
apply_figure_style(sizes=(11, 10, 9))
BASE, MID, SMALL = 11, 10, 9
GREY = "#9a9a9a"; FOCAL = "#1f4e9c"; ALARM = "#c0392b"
CAT = {"Propulsion":"#1f77b4","Structural":"#ff7f0e","Avionics/Software":"#9467bd","Human/Process":"#8c564b",
       "Staging/Separation":"#17becf","Electrical":"#bcbd22","GNC":"#e377c2","Undisclosed":GREY}
REPORT = {}

def check(fig, name):
    r = fig.canvas.get_renderer()
    texts = [(t, t.get_window_extent(r)) for t in fig.findobj(mpl.text.Text) if t.get_text().strip() and t.get_visible()]
    ov = [(a.get_text()[:25], b.get_text()[:25]) for i,(a,ba) in enumerate(texts) for b,bb in texts[i+1:] if ba.overlaps(bb)]
    fb = fig.bbox; outside = [t.get_text()[:25] for t,b in texts if b.x0 < fb.x0-1 or b.x1 > fb.x1+1 or b.y0 < fb.y0-1 or b.y1 > fb.y1+1]
    REPORT[name] = dict(overlaps=ov, outside=outside)

def save(fig, name):
    fig.savefig(f"images/{name}", dpi=200, bbox_inches="tight"); check(fig, name); plt.close(fig)

# ---------------------------------------------------------------- F1 milestones timeline
m = pd.read_csv("data/spaceflight_milestones.csv")
def lane(a):
    a = str(a)
    if a.startswith("USA"): return "USA"
    if a.startswith("USSR") or a.startswith("Russia"): return "USSR / Russia"
    if a.startswith("China"): return "China"
    if a.startswith("Europe") or a.startswith("Germany"): return "Europe"
    if a.startswith("Japan"): return "Japan"
    if a.startswith("India"): return "India"
    return "International"
m["lane"] = m.actor.map(lane)
LANES = ["USA","USSR / Russia","China","Europe","Japan","India","International"]
CATS = sorted(m.category.unique()); pal = plt.get_cmap("tab10")
CC = {c: pal(i % 10) for i,c in enumerate(CATS)}
def dec(row):
    d = str(row.date)
    if len(d) >= 10: return int(d[:4]) + (int(d[5:7])-1)/12 + (int(d[8:10])-1)/365
    return float(row.year) + 0.5
m["x"] = m.apply(dec, axis=1)
fig = plt.figure(figsize=(16, 7.6))
gs = fig.add_gridspec(1, 2, width_ratios=[1, 14], wspace=0.03)
axL, ax = fig.add_subplot(gs[0]), fig.add_subplot(gs[1], sharey=None)
for a, (lo, hi) in [(axL, (1222, 1242)), (ax, (1898, 2029))]:
    a.set_xlim(lo, hi); a.set_ylim(-0.6, len(LANES)-0.4)
    for i in range(len(LANES)): a.axhspan(i-0.5, i+0.5, color="#f4f4f4" if i % 2 == 0 else "white", zorder=0)
axL.set_yticks(range(len(LANES))); axL.set_yticklabels(LANES); axL.invert_yaxis(); ax.invert_yaxis()
ax.set_yticks([]); ax.spines["left"].set_visible(False); axL.spines["right"].set_visible(False)
axL.set_xticks([1232]); ax.set_xticks(range(1900, 2031, 10))
axL.text(1.0, -0.02, "//", transform=axL.transAxes, ha="center", va="top", fontsize=MID)
for _, r in m.iterrows():
    a = axL if r.x < 1800 else ax
    y = LANES.index(r.lane)
    a.scatter(r.x, y, s=150, color=CC[r.category], edgecolor="white", lw=0.8, zorder=3)
# staggered numbers per lane
for ln in LANES:
    sub = m[(m.lane == ln) & (m.x > 1800)].sort_values("x"); last = {-0.34: -99, 0.34: -99, -0.18: -99, 0.18: -99}
    for _, r in sub.iterrows():
        for off in (-0.34, 0.34, -0.18, 0.18):
            if r.x - last[off] > 3.2: break
        else: off = min(last, key=last.get)
        last[off] = r.x
        ax.text(r.x, LANES.index(ln) + off, str(r.num), ha="center", va="center", fontsize=SMALL, zorder=4)
for _, r in m[m.x < 1800].iterrows():
    axL.text(r.x, LANES.index(r.lane) - 0.34, str(r.num), ha="center", va="center", fontsize=SMALL)
ax.axvline(1957.76, color=GREY, lw=0.8, ls="--", zorder=1)
ax.text(1957.9, len(LANES)-0.45, "Sputnik 1", fontsize=SMALL, color="#555", va="bottom")
ax.legend(handles=[Line2D([], [], marker="o", ls="", color=CC[c], ms=9, label=c) for c in CATS],
          loc="upper center", bbox_to_anchor=(0.45, -0.09), frameon=False, fontsize=SMALL, ncol=5)
axL.set_title(f"{len(m)} spaceflight firsts, c.1232 – Sep 2026, by nation or agency (number = 'num' column in spaceflight_milestones.csv)", loc="left", fontsize=BASE, x=0)
ax.set_xlabel("Year")
save(fig, "milestones_timeline.png")

# ---------------------------------------------------------------- F2 cadence + share
c = pd.read_csv("data/launch_cadence.csv"); sh = pd.read_csv("data/launch_share.csv")
fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 5.2), gridspec_kw=dict(width_ratios=[1.7, 1], wspace=0.28))
full = c[~c.partial_year]; ytd = c[c.partial_year]
a1.bar(full.year, full.spacex_all_vehicles, color=FOCAL, label="SpaceX (all vehicles)")
a1.bar(full.year, full.other, bottom=full.spacex_all_vehicles, color="#c9d3e3", label="Rest of world")
a1.bar(ytd.year, ytd.spacex_all_vehicles, color=FOCAL, hatch="//", edgecolor="white")
a1.bar(ytd.year, ytd.other, bottom=ytd.spacex_all_vehicles, color="#c9d3e3", hatch="//", edgecolor="white")
for y in (2010, 2025):
    v = int(c.loc[c.year == y, "global_orbital_attempts"].iloc[0]); a1.text(y, v + 6, str(v), ha="center", fontsize=SMALL)
v26 = int(ytd.global_orbital_attempts.iloc[0]); a1.text(2026, v26 + 6, f"{v26}\nto 7 Oct", ha="center", fontsize=SMALL)
a1.set_xticks(range(2010, 2027, 2)); a1.set_ylabel("Orbital launch attempts"); a1.set_ylim(0, 380)
a1.legend(frameon=False, loc="upper left", fontsize=SMALL)
a1.set_title("World launch rate rose 4.5× from 2010 to 2025; SpaceX flew 52% in 2025", loc="left", fontsize=BASE)
panel_letter(a1, "a", dx=-0.08)
blocs = sh.bloc.tolist()[::-1]; yy = np.arange(len(blocs))
a2.barh(yy + 0.2, sh.set_index("bloc").loc[blocs, "2025"], height=0.38, color=FOCAL, label="2025 (330)")
a2.barh(yy - 0.2, sh.set_index("bloc").loc[blocs, "2026 YTD"], height=0.38, color="#c9d3e3", label="2026 to 7 Oct (239)")
for i, b in enumerate(blocs):
    for off, col in ((0.2, "2025"), (-0.2, "2026 YTD")):
        v = int(sh.set_index("bloc").loc[b, col]); a2.text(v + 2, i + off, str(v), va="center", fontsize=SMALL)
a2.set_yticks(yy); a2.set_yticklabels(blocs); a2.set_xlabel("Orbital launch attempts"); a2.set_xlim(0, 225)
a2.legend(frameon=False, loc="lower right", fontsize=SMALL)
a2.set_title("USA and China flew 88% of launches", loc="left", fontsize=BASE)
panel_letter(a2, "b", dx=-0.2)
save(fig, "launch_cadence.png")

# ---------------------------------------------------------------- F3 failures: causes + fix status
f = pd.read_csv("data/failures.csv")
fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 5.2), gridspec_kw=dict(wspace=0.75))
vc = f.root_cause_category.value_counts().sort_values()
a1.barh(vc.index, vc.values, color=[CAT[k] for k in vc.index])
for i, v in enumerate(vc.values): a1.text(v + 0.2, i, str(v), va="center", fontsize=SMALL)
a1.set_xlabel("Number of events"); a1.set_xlim(0, vc.max() + 2.5)
a1.set_title(f"Propulsion is the leading known cause (n = {len(f)})", loc="left", fontsize=BASE)
panel_letter(a1, "a", dx=-0.3)
order = ["Yes","By design (iterative test)","Partially","No","Too recent to assess","Not yet re-flown","N/A (vehicle retired)"]
colr = {"Yes":FOCAL,"By design (iterative test)":"#6b8cc7","Partially":"#e0a64a","No":ALARM,"Too recent to assess":"#cfcfcf","Not yet re-flown":"#bdbdbd","N/A (vehicle retired)":"#e8e8e8"}
fh = f.did_fix_hold.value_counts().reindex(order).fillna(0).astype(int)[::-1]
a2.barh(fh.index, fh.values, color=[colr[k] for k in fh.index], edgecolor="#999", lw=0.4)
for i, v in enumerate(fh.values): a2.text(v + 0.2, i, str(v), va="center", fontsize=SMALL)
a2.set_xlabel("Number of events"); a2.set_xlim(0, fh.max() + 2.5)
a2.set_title(f"Did the fix hold? {fh['No']} failed on a later flight", loc="left", fontsize=BASE)
panel_letter(a2, "b", dx=-0.45)
save(fig, "failures_overview.png")

# ---------------------------------------------------------------- F4 learning loop
ms = pd.read_csv("osalr/osalr_master.csv"); tx = pd.read_csv("osalr/failure_mode_taxonomy.csv")
ms["era"] = pd.cut(ms.year, [1900, 1999, 2019, 2025, 2030], labels=["1957–1999","2000–2019","2020–2025","2026"])
ms["rec"] = np.where(ms.root_cause_recurred.str.startswith("Yes"), "Repeated a known mode",
             np.where(ms.root_cause_recurred.str.startswith("No"), "New mode", "Unknown (no public cause)"))
ct = pd.crosstab(ms.era, ms.rec).reindex(columns=["Repeated a known mode","New mode","Unknown (no public cause)"], fill_value=0)
fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 10.5), gridspec_kw=dict(height_ratios=[1, 1.6], hspace=0.35))
left = np.zeros(len(ct)); cols = [ALARM, FOCAL, GREY]
for col, cl in zip(ct.columns, cols):
    a1.barh(ct.index.astype(str), ct[col], left=left, color=cl, label=col)
    for i, (l, v) in enumerate(zip(left, ct[col])):
        if v: a1.text(l + v/2, i, str(v), ha="center", va="center", fontsize=SMALL, color="white" if cl != GREY else "black")
    left += ct[col].values
a1.invert_yaxis(); a1.set_xlabel("Number of events"); a1.set_xlim(0, left.max() + 1)
a1.legend(frameon=False, loc="upper left", bbox_to_anchor=(1.0, 1.0), fontsize=SMALL)
known = ms[ms.rec != "Unknown (no public cause)"]; nrep = (known.rec == "Repeated a known mode").sum()
a1.set_title(f"{nrep} of {len(known)} events with known recurrence status repeated an earlier mode", loc="left", fontsize=BASE)
panel_letter(a1, "a", dx=-0.12)
rows = []
for _, t in tx[tx.code != tx.parent_class].iterrows():
    hit = ms[ms.failure_mode_codes.str.split(";").apply(lambda L: t.code in L)]
    rows.append((t.code, t.mode_name, len(hit), hit.org_country.nunique()))
cov = pd.DataFrame(rows, columns=["code","mode","n_events","n_orgs"]).sort_values(["n_orgs","n_events"]).tail(12)
yy = np.arange(len(cov))
a2.hlines(yy, 0, cov.n_orgs, color="#bbb", lw=1.5)
a2.scatter(cov.n_orgs, yy, s=70, color=[GREY if c == "UNK-UNDISC" else FOCAL for c in cov.code], zorder=3)
for i, (o_, e_) in enumerate(zip(cov.n_orgs, cov.n_events)): a2.text(o_ + 0.25, i, f"{o_} orgs / {e_} events", va="center", fontsize=SMALL)
a2.set_yticks(yy); a2.set_yticklabels([f"{md} ({cd})" for cd, md in zip(cov.code, cov["mode"])])
a2.set_xlabel("Distinct organizations affected"); a2.set_xlim(0, cov.n_orgs.max() + 3.2)
a2.set_title("Failure modes shared by the most organizations (top 12)", loc="left", fontsize=BASE)
panel_letter(a2, "b", dx=-0.6)
save(fig, "learning_loop.png")

# ---------------------------------------------------------------- F5 cost
lc = pd.read_csv("data/launch_costs.csv").sort_values("cost_per_kg_usd"); cm = pd.read_csv("data/cost_model.csv")
fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 11.5), gridspec_kw=dict(hspace=0.32))
reuse = lc.vehicle.str.contains(r"reused|Falcon Heavy|New Glenn|Shuttle")
yy = np.arange(len(lc))
for i, (_, r) in enumerate(lc.iterrows()):
    proj = "projected" in r.vehicle
    a1.scatter(r.cost_per_kg_usd, i, s=70, facecolor="white" if proj else (FOCAL if reuse.iloc[i] else GREY), edgecolor=FOCAL if (proj or reuse.iloc[i]) else GREY, lw=1.5, zorder=3)
    a1.text(r.cost_per_kg_usd * 1.25, i, f"${r.cost_per_kg_usd:,.0f}", va="center", fontsize=SMALL)
a1.set_yticks(yy); a1.set_yticklabels([f"{v} ({y})" if "projected" not in v else "Starship (company target)" for v, y in zip(lc.vehicle, lc.year)])
a1.set_xscale("log"); a1.set_xlim(50, 300000); a1.set_xlabel("Approx. price per kg to LEO (USD, log scale)")
a1.xaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda v, _: f"${v/1000:g}k" if v >= 1000 else f"${v:g}"))
a1.legend(handles=[Line2D([],[],marker="o",ls="",color=FOCAL,label="Reusable / partly reusable"),Line2D([],[],marker="o",ls="",color=GREY,label="Expendable"),
                   Line2D([],[],marker="o",ls="",mfc="white",mec=FOCAL,label="Company target (not demonstrated)")], frameon=False, loc="lower right", fontsize=SMALL)
a1.set_title("Reusable Falcon-family boosters are cheapest per kg; the partly reusable Shuttle was the costliest", loc="left", fontsize=BASE); panel_letter(a1, "a", dx=-0.3)
cm = cm.sort_values("effective_usd_per_kg"); yy = np.arange(len(cm))
for i, (_, r) in enumerate(cm.iterrows()):
    tgt = "target" in r.vehicle
    col = FOCAL if r.vehicle == "Falcon 9" else GREY
    a2.scatter(r.effective_usd_per_kg, i, s=70, facecolor="white" if tgt else col, edgecolor=FOCAL if tgt else col, lw=1.5, zorder=3)
    a2.text(r.effective_usd_per_kg * 1.25, i, f"${r.effective_usd_per_kg:,.0f}", va="center", fontsize=SMALL)
a2.set_yticks(yy); a2.set_yticklabels([f"{v} — {k}, {o}" for v, k, o in zip(cm.vehicle, cm.contract_type, cm.destination_orbit)])
a2.set_xscale("log"); a2.set_xlim(50, 300000); a2.set_xlabel("Contract price ÷ payload capacity (USD/kg, log scale)")
a2.xaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda v, _: f"${v/1000:g}k" if v >= 1000 else f"${v:g}"))
f9 = cm[cm.vehicle == "Falcon 9"].effective_usd_per_kg
a2.set_title(f"Same rocket, {f9.max()/f9.min():.0f}× price spread by contract (Falcon 9 in blue)", loc="left", fontsize=BASE); panel_letter(a2, "b", dx=-0.62)
save(fig, "cost_per_kg.png")

# ---------------------------------------------------------------- F6 funding
fu = pd.read_csv("data/funding.csv")
gov = fu[fu.entity_type.str.contains("Government|Multinational")].dropna(subset=["annual_budget_or_revenue_busd"])
gv = [(f"{r.entity} (FY{int(r.budget_year)})" if r.entity == "NASA" else f"{r.entity} ({int(r.budget_year)})", r.annual_budget_or_revenue_busd, False) for _, r in gov.iterrows()]
gv.append(("China (independent est., 2024)", 16.5, True)); gv = sorted(gv, key=lambda t: t[1])
fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 8.5), gridspec_kw=dict(hspace=0.45))
for i, (n, v, est) in enumerate(gv):
    a1.barh(i, v, color="white" if est else FOCAL, edgecolor=FOCAL, hatch="//" if est else None)
    if est: a1.errorbar(v, i, xerr=[[2.5], [2.5]], color="k", capsize=4, lw=1)
    a1.text((v + (2.9 if est else 0.4)), i, ("$14–19B" if est else f"${v:.1f}B"), va="center", fontsize=SMALL)
a1.set_yticks(range(len(gv))); a1.set_yticklabels([g[0] for g in gv]); a1.set_xlim(0, 30); a1.set_xlabel("Annual budget (USD billions)")
a1.set_title("NASA's budget exceeds ESA, Roscosmos, JAXA and ISRO combined", loc="left", fontsize=BASE); panel_letter(a1, "a", dx=-0.38)
pv = [("SpaceX — revenue (2024 est.)", 13.1), ("SpaceX — capital raised (cumulative est.)", 12.0), ("Chinese commercial launch — raised (est.)", 8.0),
      ("Relativity Space — raised", 1.5), ("Rocket Lab — revenue (2024)", 0.44), ("Firefly — revenue (2024)", 0.06)][::-1]
a2.barh(range(len(pv)), [v for _, v in pv], color=GREY)
for i, (_, v) in enumerate(pv): a2.text(v + 0.25, i, f"${v:g}B", va="center", fontsize=SMALL)
a2.set_yticks(range(len(pv))); a2.set_yticklabels([n for n, _ in pv]); a2.set_xlim(0, 16); a2.set_xlabel("USD billions")
a2.set_title("Private money is concentrated in one company", loc="left", fontsize=BASE); panel_letter(a2, "b", dx=-0.5)
save(fig, "funding.png")

# ---------------------------------------------------------------- F7 tech gaps
tg = pd.read_csv("data/tech_gaps.csv").sort_values("current_trl")
fig, ax = plt.subplots(figsize=(11, 5.6)); yy = np.arange(len(tg))
ax.hlines(yy, 1, tg.current_trl, color="#bbb", lw=2)
ax.scatter(tg.current_trl, yy, s=90, color=[FOCAL if (e and not e.startswith("No ")) else GREY for e in tg.evidence_2026.fillna("")], zorder=3)
ax.axvline(9, color=GREY, ls="--", lw=0.8); ax.text(8.95, len(tg) - 0.4, "TRL 9 = flight-proven", ha="right", fontsize=SMALL, color="#555")
ax.set_yticks(yy); ax.set_yticklabels(tg.capability); ax.set_xlim(1, 9.3); ax.set_xticks(range(1, 10)); ax.set_xlabel("Technology readiness level (analyst estimate)")
ax.legend(handles=[Line2D([],[],marker="o",ls="",color=FOCAL,label="2026 flight evidence (see tech_gaps.csv)"),Line2D([],[],marker="o",ls="",color=GREY,label="No new 2026 evidence")], frameon=False, loc="lower right", fontsize=SMALL)
ax.set_title("All 12 tracked interplanetary capabilities are below TRL 7", loc="left", fontsize=BASE)
save(fig, "tech_gaps.png")
for k, v in REPORT.items():
    print(f"{k:28s} label overlaps: {len(v['overlaps'])}")
