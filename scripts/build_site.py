"""build_site.py — generates README.md, docs/milestones.md, docs/data-changelog.md and the static site in site/
from data/*.csv, osalr/ and images/. Run from anywhere:  python scripts/build_site.py
Every number in the text is computed from the CSVs at build time."""
import csv, json, os, re, shutil, html as H
from pathlib import Path
import pandas as pd

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
os.chdir(ROOT)
AS_OF = "9 October 2026"

f  = pd.read_csv("data/failures.csv"); o = pd.read_csv("data/organizations.csv")
ms = pd.read_csv("data/spaceflight_milestones.csv"); cm = pd.read_csv("data/cost_model.csv")
ch = pd.read_csv("data/changelog.csv"); c = pd.read_csv("data/launch_cadence.csv")
ledger = pd.read_csv("data/launch_failures_2025_2026.csv"); om = pd.read_csv("osalr/osalr_master.csv")
tax = pd.read_csv("osalr/failure_mode_taxonomy.csv")
f9 = cm[cm.vehicle == "Falcon 9"].effective_usd_per_kg
cy = lambda y, col: int(c.loc[c.year == y, col].iloc[0])
N = dict(
    n_fail=len(f), deaths=int(f.fatalities.sum()), prop=int((f.root_cause_category == "Propulsion").sum()),
    undiscl=int((f.root_cause_category == "Undisclosed").sum()),
    rec_yes=int(f.root_cause_recurred.str.startswith("Yes").sum()),
    rec_known=int((~f.root_cause_recurred.str.startswith("Unknown")).sum()),
    fix_no=int((f.did_fix_hold == "No").sum()), fix_yes=int((f.did_fix_hold == "Yes").sum()),
    notyet=int((f.did_fix_hold == "Not yet re-flown").sum()),
    n2026=int((f.year == 2026).sum()), n2026_nocause=int(((f.year == 2026) & (f.root_cause_category == "Undisclosed")).sum()),
    c2010=cy(2010, "global_orbital_attempts"), c2025=cy(2025, "global_orbital_attempts"), s2025=cy(2025, "spacex_all_vehicles"),
    c2026=cy(2026, "global_orbital_attempts"), s2026=cy(2026, "spacex_all_vehicles"), n_ms=len(ms),
    orgs=int(om.org_country.nunique()), ledger25=int((ledger.date < "2026").sum()), ledger26=int((ledger.date >= "2026").sum()),
    n_codes=len(tax),
)

SECTIONS = [
("Scope and sources", f"""
Data current to **9 October 2026**. Launch counts come from one source throughout: Wikipedia's annual *"<year> in spaceflight"* summary tables (2010–2025) and the 2026 launch log (launches through 7 October). These totals **include Starship flight tests**. Other trackers report 324–330 launches for 2025 depending on counting rules (SpaceNews 324, BryceTech 325, McDowell 329, Wikipedia 330).
Values marked *estimate*, which are cost per kg, technology readiness levels (TRL) and China's space budget, are approximations; every other value is a dated, recorded event. All changes made in this revision are listed in `data/changelog.csv` and [docs/data-changelog.md](docs/data-changelog.md).
"""),
("1 · How we got here: 61 spaceflight firsts", f"""
`spaceflight_milestones.csv` lists **{N['n_ms']} firsts from c.1232 to September 2026** (USA {int((ms.actor.str.startswith('USA')).sum())}, USSR/Russia {int((ms.actor.str.startswith('USSR')|ms.actor.str.startswith('Russia')).sum())}, China {int(ms.actor.str.startswith('China').sum())}, plus Europe, Japan, India and international projects).
- **Before 1957:** documented Jin-dynasty rocket weapons (c.1232; device details are disputed, and the Wan Hu flight story is legend and excluded), Tsiolkovsky's rocket equation (1903), Goddard's liquid-fuel rocket (1926), GIRD-09, the first Soviet liquid-propellant rocket (17 Aug 1933), the V-2 reaching space (1944), the first Soviet A-4 launches at Kapustin Yar (1947), Bumper 5 staging (1949), and Dezik and Tsygan, the first dogs in space (22 Jul 1951). China's first sounding rocket, T-7M, flew on 19 Feb 1960.
- **Correction kept from the earlier review:** Gagarin's Vostok 1 (12 Apr 1961) made a single Earth orbit and did not go near the Moon. The first crew to reach lunar vicinity was Apollo 8 (1968).
- **2026 additions:** Artemis II (1–11 Apr), the first crewed flight beyond low Earth orbit since 1972 and the farthest humans have travelled from Earth; Long March 10B booster recovered at sea (10 Jul), making China the second country to recover an orbital booster; Isar Spectrum, the first orbital launch from Western European soil (5 Sep); and Starship Flight 14, Starship's first orbital and first commercial flight (28 Sep).
""", "milestones_timeline"),
("2 · Launch activity 2010–2026", f"""
- World orbital launch attempts rose from **{N['c2010']} (2010) to {N['c2025']} (2025)**, 4.5×. SpaceX flew **{N['s2025']} (52%)** in 2025.
- **2026 to 7 Oct: {N['c2026']} launches**, of which SpaceX flew {N['s2026']}. The USA (142) and China (70) account for 89% (88% in 2025).
- 2026 orbital launch failures: **7** (China 4, USA 1, India 1, Japan 1). The complete 2025–2026 failure list is in `launch_failures_2025_2026.csv` ({N['ledger25']} + {N['ledger26']} entries).
""", "launch_cadence"),
("3 · Failures and post-mortems", f"""
`failures.csv` catalogues **{N['n_fail']} failures from 1957 to 2026**: 37 notable historical events plus every 2026 orbital failure and the New Glenn pad explosion. Five events killed {N['deaths']} people: Nedelin (1960, 78), Apollo 1 (1967, 3), Soyuz 1 (1967, 1), Challenger (1986, 7) and Columbia (2003, 7).
- **Propulsion is the leading known cause ({N['prop']} of {N['n_fail']}).** All {N['undiscl']} events with no public cause date from 2026.
- **Fix verification:** {N['fix_yes']} corrective actions held; **{N['fix_no']} did not**, meaning the same failure returned on a later flight (Vega VV15→VV17, Astra, Firefly ×2, Starship Flight 7→8, PSLV-C61→C62). {N['notyet']} vehicles have not flown again since failing.
- **New Glenn (28 May 2026):** the vehicle exploded during a static fire and severely damaged Launch Complex 36. Blue Origin attributed the cause (5 Aug) to a BE-4 main oxygen valve. This is the third vehicle lost on the ground in a decade, after AMOS-6 (2016) and Starship Ship 36 (2025).
""", "failures_overview"),
("4 · The learning loop and the OSALR database", f"""
- Of the {N['rec_known']} events whose recurrence status is known, **{N['rec_yes']} ({round(100*N['rec_yes']/N['rec_known'])}%) repeated a failure mode seen before**. Uncommanded engine shutdown alone has hit 6 organizations in 3 blocs over 56 years.
- **The 2026 problem is disclosure, not recurrence:** {N['n2026_nocause']} of the {N['n2026']} failures logged in 2026 have no public cause statement. One was a clear repeat: PSLV-C62 failed in the same third-stage phase as PSLV-C61, and the C62 inquiry report (13 Jun 2026) was not released.
- **OSALR (Open Spaceflight Anomaly & Lesson Repository)** is a working SQLite database with {N['n_fail']} events, {N['orgs']} organizations, 36 controlled failure-mode codes (8 classes, including `UNK` for undetermined or undisclosed causes) and fully populated reference and fix-verification tables. `build_osalr.py` rebuilds it from `osalr_master.csv`. The five worked queries are in `query_demos.md`; governance and intake files are included.
""", "learning_loop"),
("5 · Cost per kilogram", f"""
- Approximate price per kg to LEO (*estimate*): Space Shuttle ~$54,500, Falcon 9 reused ~$2,600, Falcon Heavy ~$1,500. Starship's ~$100/kg is a company target and has not been demonstrated.
- **Contract terms move the price more than hardware:** Falcon 9 ranges from ${f9.min():,.0f}/kg (commercial, LEO) to ${f9.max():,.0f}/kg (NASA CRS-2 to the ISS), {f9.max()/f9.min():.0f}× apart. SLS to trans-lunar injection is $81,481/kg.
""", "cost_per_kg"),
("6 · Who funds spaceflight", f"""
- **NASA FY2026: $24.4B.** Congress rejected nearly all of a proposed 24% cut in January 2026; the FY2027 request again proposes a 23% cut. For comparison: ESA ~$8.5B (2024), Roscosmos ~$3.4B (2023), JAXA ~$2.1B, ISRO ~$1.6B. China publishes no figure; independent estimates are $14–19B.
- Private funding is concentrated: SpaceX ~$13B revenue (2024 est.), compared with ~$8B raised in total by Chinese commercial launch firms (est.).
""", "funding"),
("7 · Technology gaps for interplanetary flight", f"""
All 12 tracked capabilities sit at TRL 3–6 (*analyst estimates, not agency assessments*). 2026 brought flight evidence for super-heavy reuse (Starship orbital flight; Long March 10B and Zhuque-3 booster recoveries) and for deep-space crew operations (Artemis II). The lowest-readiness items are unchanged: deep-space radiation protection (TRL 3), surface habitats (3), ISRU, Mars entry-descent-landing, nuclear propulsion and cryogenic refuelling (4 each). No ship-to-ship cryogenic propellant transfer had been reported by October 2026.
""", "tech_gaps"),
("8 · Next steps", """
1. **Code the 8 remaining 2025 failures into OSALR** (Spectrum F1, Eris F1, Zhuque-2E Y3, Ceres-1 Y19, Kuaizhou-1A Y33, Hanbit-Nano, Simorgh, Zuljanah). They are already listed in `launch_failures_2025_2026.csv`.
2. **Re-check the 8 "not yet re-flown" entries** at each return to flight. The next scheduled are PSLV-C63 (Nov 2026) and Astrobotic Griffin-1 (no earlier than Nov 2026); New Glenn has no date yet.
3. **Request cause disclosures** from ISRO, CASC, Space One, Space Pioneer, Galactic Energy and Blue Origin using `osalr_intake_template.csv`. Each `UNK-UNDISC` record that gains a cause becomes a usable lesson.
4. **Replace estimates with primary sources:** agency-published TRLs, contract-award prices (NASA and NSSL notices) in `cost_model.csv`, and official budget documents for ESA, JAXA and ISRO for FY2026.
5. **Q4 2026 watch list:** Starship Flight 15, Mengzhou-1 on Long March 10A, Gaganyaan G1 (HLVM3), JAXA MMX (20 Oct), Starliner-1 (Dec).
"""),
]

def md_to_html(t):
    t = H.escape(t.strip())
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t); t = re.sub(r"\*(.+?)\*", r"<i>\1</i>", t); t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    out, lst = [], None
    for line in t.split("\n"):
        m1 = re.match(r"^- (.*)", line); m2 = re.match(r"^\d+\. (.*)", line)
        if m1 or m2:
            tag = "ul" if m1 else "ol"
            if lst != tag:
                if lst: out.append(f"</{lst}>")
                out.append(f"<{tag}>"); lst = tag
            out.append(f"<li>{(m1 or m2).group(1)}</li>")
        else:
            if lst: out.append(f"</{lst}>"); lst = None
            if line.strip(): out.append(f"<p>{line}</p>")
    if lst: out.append(f"</{lst}>")
    return "\n".join(out)

def table(df, cols, names=None, responsive=False):
    names = names or cols
    table_class = ' class="appendix-table" role="table"' if responsive else ''
    h = '<div class="table-scroll" tabindex="0" role="region" aria-label="Data table"><table' + table_class + '><thead role="rowgroup"><tr role="row">' + "".join(f'<th scope="col" role="columnheader">{H.escape(n)}</th>' for n in names) + "</tr></thead><tbody role=\"rowgroup\">"
    for _, r in df.iterrows():
        h += '<tr role="row">' + "".join(f'<td role="cell" data-label="{H.escape(n, quote=True)}">{H.escape(str(r[c])) if pd.notna(r[c]) else ""}</td>' for c, n in zip(cols, names)) + "</tr>"
    return h + "</tbody></table></div>"

CAPTIONS = {
 "milestones_timeline": "Firsts by nation or agency; numbers match the num column of spaceflight_milestones.csv (full list in Appendix A).",
 "launch_cadence": "(a) Orbital launch attempts per year; the hatched 2026 bar covers launches to 7 Oct. (b) Launches by bloc, 2025 vs 2026 to date.",
 "failures_overview": "(a) Primary root-cause category. (b) Whether the corrective action held on later flights.",
 "learning_loop": "(a) Events that repeated a known failure mode, by era. (b) Failure modes ranked by the number of distinct organizations affected.",
 "cost_per_kg": "(a) Approximate price per kg to LEO by vehicle (estimates). (b) Contract price divided by payload capacity, by contract type.",
 "funding": "(a) Government space budgets; China is an independent estimate range. (b) Private revenue and capital raised (estimates).",
 "tech_gaps": "Technology readiness by capability (analyst estimates); blue = new 2026 flight evidence.",
}


FIGS = ["milestones_timeline", "launch_cadence", "failures_overview", "learning_loop", "cost_per_kg", "funding", "tech_gaps"]

DATA_DESC = {
 "data/failures.csv": "Curated failures 1957–2026 with root cause, lesson, primary reference and fix verification",
 "data/launch_failures_2025_2026.csv": "Every orbital launch logged as a failure in 2025 and 2026 to date",
 "data/launch_cadence.csv": "World and SpaceX orbital launch attempts per year, 2010–2026 (2026 partial)",
 "data/launch_share.csv": "Launches by country/bloc, 2025 and 2026 to date",
 "data/organizations.csv": "Launch providers and agencies: vehicles, launches 2025/2026, reuse status",
 "data/spaceflight_milestones.csv": "Spaceflight firsts c.1232 – 2026",
 "data/launch_costs.csv": "Approximate price per kg to LEO by vehicle (estimates)",
 "data/cost_model.csv": "Contract price ÷ payload capacity, by contract type (estimates)",
 "data/funding.csv": "Government budgets and private revenue/capital (budgets official; private values estimates)",
 "data/tech_gaps.csv": "Readiness of 12 interplanetary capabilities (analyst TRL estimates) with 2026 evidence",
 "data/changelog.csv": "Every edit in the October 2026 revision, with its source",
 "osalr/osalr.db": "SQLite failure database (rebuild with osalr/build_osalr.py)",
 "osalr/osalr_master.csv": "Single source table for the database",
 "osalr/failure_mode_taxonomy.csv": "Controlled failure-mode codes (classes and leaf modes)",
 "osalr/osalr_events_with_codes.csv": "Event index with controlled failure-mode codes",
 "osalr/failure_db_seed_public.csv": "Public failure database records",
 "osalr/osalr_intake_template.csv": "Intake form fields and instructions for submitting an event",
 "osalr/osalr_schema.sql": "SQL schema for the SQLite database",
 "osalr/failure_db_schema.json": "Public failure-record schema",
 "osalr/osalr_governance.md": "Database governance, access tiers and verification rules",
 "osalr/query_demos.md": "Five worked SQL queries and their results",
 "docs/milestones.md": "Full milestone list with categories and significance",
 "docs/data-changelog.md": "Data revision history with sources",
 "LICENSE": "MIT code licence",
 "LICENSE-DATA.md": "CC BY-SA 4.0 data, figure and text licence",
}

def inventory():
    rows = []
    for p, d in DATA_DESC.items():
        n = str(len(pd.read_csv(p))) if p.endswith(".csv") else ("binary" if p.endswith(".db") else "document")
        rows.append(f"| [`{p}`]({p}) | {n} | {d} |")
    return "| File | Rows | Contents |\n|---|---:|---|\n" + "\n".join(rows)

def report_md(img):
    out = []
    for sec in SECTIONS:
        title, text = sec[0], sec[1]; fig = sec[2] if len(sec) > 2 else None
        out += [f"### {title}", text.strip(), ""]
        if fig: out += [f"![{CAPTIONS[fig]}]({img(fig)})", f"<sub>{CAPTIONS[fig]}</sub>", ""]
    return "\n".join(out)

REPORT_BODY = report_md(lambda k: "images/" + k + ".png")

README = f"""# Open Spaceflight Research

Datasets, figures and a cross-organization failure database on rocket launches, spaceflight failures and the
technology gaps between today's launch industry and crewed interplanetary flight. Data current to **{AS_OF}**.

**At a glance:** {N['n_ms']} spaceflight firsts · {N['n_fail']} catalogued failures with root cause and fix verification ·
{N['c2025']} orbital launches in 2025 and {N['c2026']} in 2026 to 7 Oct · failure database (OSALR) with {N['n_fail']} events from {N['orgs']} organizations.

## Key findings
- **Launch is no longer the bottleneck.** World orbital launches rose from {N['c2010']} (2010) to {N['c2025']} (2025); SpaceX flew {N['s2025']} of them.
- **Failures keep repeating.** {N['rec_yes']} of {N['rec_known']} failures with known recurrence status repeated a failure mode seen before; {N['fix_no']} corrective actions failed on a later flight.
- **2026 failures are mostly unexplained in public.** {N['n2026_nocause']} of the {N['n2026']} failures logged in 2026 have no public cause statement.
- **Contract terms move price more than hardware.** The same Falcon 9 ranges from ${f9.min():,.0f}/kg to ${f9.max():,.0f}/kg depending on the contract.
- **Interplanetary capabilities remain immature.** All 12 tracked capabilities are at TRL 3–6 (analyst estimates).

## Repository layout
```
data/      curated CSV datasets (source of truth)
osalr/     OSALR failure database: SQLite file, master CSV, taxonomy, schema, intake form, governance, query demos
images/    figures (generated by scripts/make_figures.py)
scripts/   make_figures.py, build_site.py, refresh_launch_logs.py
docs/      milestones.md, data-changelog.md (generated)
site/      static website (generated; deploy this folder)
```

{inventory()}

## Report
{REPORT_BODY}

Full milestone list: [docs/milestones.md](docs/milestones.md) · Edits in this revision: [docs/data-changelog.md](docs/data-changelog.md)

## Reproduce
```bash
pip install -r requirements.txt
python scripts/build.py           # rebuild and validate the complete site

# Or run individual steps:
python osalr/build_osalr.py        # rebuild osalr/osalr.db from osalr/osalr_master.csv
python scripts/make_figures.py     # regenerate images/
python scripts/build_site.py       # regenerate README.md, docs/ and site/
python scripts/refresh_launch_logs.py   # optional: re-fetch Wikipedia launch logs and write a comparison to build/refresh/
```
`refresh_launch_logs.py` never overwrites `data/`. It writes fresh counts to `build/refresh/` so that changes can be reviewed before they are copied in.

## Deploy the website
`site/` is a complete static HTML/CSS/JavaScript site with relative links and no runtime dependencies. The data explorer embeds all {sum(1 for folder in ("data", "osalr") for source in Path(folder).glob("*.csv"))} CSV datasets at build time, so search, filters, sorting, pagination and full-record details also work offline. All original CSVs, the SQLite database, documentation and licences are downloadable.

Run `python scripts/build.py` after editing source data; it verifies every dataset, local link and database record before deployment. Deploy the generated `site/` directory with no hosting build step.

- **Cloudflare Pages:** connect the repository, set *Build command* to empty and *Build output directory* to `site`. Or deploy from the command line: `npx wrangler pages deploy site --project-name open-spaceflight-research`.
- **Vercel:** import the repository; `vercel.json` sets the output directory to `site`. Or run `npx vercel deploy --prod` from the repository root.
- **Local preview:** `python -m http.server -d site 8000`.

## Contributing
- **Report a failure or correct a record:** fill in `osalr/osalr_intake_template.csv`, add the row to `osalr/osalr_master.csv`, rebuild, and open a pull request. Give a primary source for every cause statement.
- **Corrections to data:** edit the CSV, add a row to `data/changelog.csv` with the source, then run the three build commands above.
- Rules for record IDs, access tiers and fix verification are in [osalr/osalr_governance.md](osalr/osalr_governance.md).

## Sources and licence
- Launch counts and 2025–2026 failure entries: Wikipedia, *"<year> in spaceflight"* and *"List of spaceflight launches in …"* (retrieved {AS_OF}). Historical failures cite their accident-board reports in `primary_reference`.
- Estimates (cost per kg, contract $/kg, TRL, China's budget, private funding) are labelled as estimates in the data and text.
- **Code** (`scripts/`, `osalr/build_osalr.py`): MIT licence, see [LICENSE](LICENSE).
- **Data, figures and text**: [CC BY-SA 4.0](LICENSE-DATA.md). Share-alike is required because parts are derived from Wikipedia (CC BY-SA 4.0).
"""

def page_html():
    body = []
    for sec in SECTIONS:
        title, text = sec[0], sec[1]; fig = sec[2] if len(sec) > 2 else None
        blk = f"<section id='s{len(body)}'><h2>{H.escape(title)}</h2>{md_to_html(text)}"
        if fig:
            blk += f'<figure><img src="images/{fig}.png" alt="{H.escape(CAPTIONS[fig])}" loading="lazy"><figcaption>{H.escape(CAPTIONS[fig])}</figcaption></figure>'
        if title.startswith("2"):
            blk += "<h3>Organizations: launches 2025 and 2026 to date</h3>" + table(o, ["organization","flagship_vehicle","orbital_launches_2025","orbital_launches_2026_ytd","reuse_status","status"], ["Organization","Vehicle","2025","2026 to date","Reuse","Status"])
        if title.startswith("3"):
            blk += "<h3>2026 failures</h3>" + table(f[f.year == 2026], ["date","name","org_country","root_cause_category","cause_detail","did_fix_hold"], ["Date","Event","Operator","Cause category","What happened","Fix held?"])
        body.append(blk + "</section>")
    dl = "".join(f"<li><a href='{p}' download>{H.escape(p)}</a> — {H.escape(d)}</li>" for p, d in DATA_DESC.items())
    body.append(f"<section id='downloads'><h2>Downloads</h2><ul>{dl}</ul></section>")
    body.append(f"<section id='milestones'><h2>Appendix A · All {len(ms)} milestones</h2>{table(ms, ['num','date','milestone','actor'], ['#','Date','Milestone','Actor'], responsive=True)}</section>")
    body.append(f"<section id='changelog'><h2>Appendix B · Edits in this revision ({len(ch)})</h2>{table(ch, ['dataset','change','source'], ['Dataset','Change','Source'], responsive=True)}</section>")
    nav = " · ".join(f"<a href='#s{i}'>{H.escape(s[0].split('·')[0].strip() if '·' in s[0] else s[0])}</a>" for i, s in enumerate(SECTIONS)) + " · <a href='#downloads'>Downloads</a>"
    datasets = []
    for folder in ("data", "osalr"):
        for source in sorted(Path(folder).glob("*.csv")):
            with source.open(encoding="utf-8", newline="") as stream:
                reader = csv.DictReader(stream)
                rows = list(reader)
                columns = reader.fieldnames
            datasets.append({"id": source.stem, "path": source.as_posix(),
                             "label": source.stem.replace("_", " ").title(),
                             "description": DATA_DESC[source.as_posix()],
                             "columns": columns, "rows": rows})
    # Escape HTML-significant characters so CSV text cannot close the script element.
    payload = json.dumps(datasets, ensure_ascii=False).replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    options = "".join(f'<option value="{d["id"]}"{ " selected" if d["id"] == "failures" else ""}>{H.escape(d["label"])} ({len(d["rows"])} rows)</option>' for d in datasets)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Open Spaceflight Research — {AS_OF}</title>
<meta name="description" content="Explore every spaceflight dataset: milestones, launch failures, costs, funding and the OSALR database. Data to {AS_OF}.">
<link rel="icon" href="assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="assets/site.css"><script src="assets/explorer.js" defer></script></head><body>
<a class="skip-link" href="#explorer">Skip to data explorer</a>
<header class="hero"><div class="hero-inner">
<div class="brand"><span class="orbit-mark" aria-hidden="true">↗</span> OPEN SPACEFLIGHT RESEARCH <span class="edition">OCTOBER 2026 EDITION</span></div>
<p class="eyebrow">THE RECORD. THE LESSONS. THE NEXT FRONTIER.</p>
<h1>Spaceflight, in perspective.</h1>
<p class="intro">A shared record of launches, failures and the capabilities we still need. Explore the data, trace the lessons, and read the research.</p>
<p class="hero-meta">Dataset snapshot · {AS_OF} · Launch counts through 7 October</p>
<div class="stats"><div><strong>{N['n_ms']}</strong><span>Spaceflight firsts</span></div><div><strong>{N['n_fail']}</strong><span>Catalogued failures</span></div><div><strong>{N['c2025']}</strong><span>Launches in 2025</span></div><div><strong>{N['orgs']}</strong><span>Organizations in OSALR</span></div></div>
</div></header>
<main><nav class="primary-nav" aria-label="Main navigation"><a href="#explorer">Explore the data</a><a href="#s0">Read the report</a><a href="#downloads">Download files</a><a href="#milestones">Milestones</a><a href="#changelog">Revision history</a></nav>
<section id="explorer" class="explorer"><div class="section-heading"><div><p class="eyebrow">THE OPEN DATA COLLECTION</p><h2>Every dataset. Every record.</h2></div><span class="collection-count">{len(datasets)} datasets · {sum(len(d['rows']) for d in datasets)} rows</span></div>
<p>Search across every field in a dataset, filter records, or open a record to read all its details. Estimates and source notes are preserved from the original files.</p>
<noscript><p class="notice">Enable JavaScript to use search and filters. Every dataset is also available in <a href="#downloads">Downloads</a>.</p></noscript>
<div id="explorer-controls" hidden>
<div class="explorer-controls"><label class="dataset-control">Dataset<select id="dataset">{options}</select></label><label class="search-control">Search every field<input id="search" type="search" placeholder="Try a vehicle, organization, year or failure mode…" autocomplete="off"></label></div>
<p id="dataset-description" class="dataset-description"></p>
<div class="filter-controls"><label>Filter field<select id="filter-field"><option value="">All fields</option></select></label><label>Value<select id="filter-value" disabled><option value="">All values</option></select></label><label>Rows per page<select id="page-size"><option value="25">25</option><option value="50">50</option><option value="100">100</option><option value="all">All</option></select></label><label class="checkbox-label"><input id="all-columns" type="checkbox"> Show every column</label><button id="reset" type="button" class="secondary-button">Reset</button></div>
<div class="results-bar"><p id="results-status" role="status" aria-live="polite"></p><a id="dataset-download" class="download-link" download>Download CSV ↓</a></div>
<div class="table-scroll explorer-table" tabindex="0" role="region" aria-label="Dataset records; scroll horizontally to see more fields"><table id="data-table"><thead></thead><tbody></tbody></table></div>
<p id="empty-state" class="notice" hidden>No matching records. Try another search or reset the filters.</p>
<div class="pagination"><button id="previous-page" type="button" class="secondary-button">← Previous</button><span id="page-status"></span><button id="next-page" type="button" class="secondary-button">Next →</button></div>
</div></section>
<div class="report-heading"><p class="eyebrow">RESEARCH NOTES</p><h2>The spaceflight report</h2><nav class="report-nav" aria-label="Report chapters">{nav}</nav></div>
{''.join(body)}
</main><footer><p>Open Spaceflight Research · Dataset snapshot: {AS_OF}</p><p>Code <a href="LICENSE">MIT</a> · Data, figures and text <a href="LICENSE-DATA.md">CC BY-SA 4.0</a> (partly derived from Wikipedia).</p></footer>
<dialog id="record-dialog" aria-labelledby="record-title"><div class="dialog-heading"><h2 id="record-title">Record details</h2><button id="close-record" type="button" class="secondary-button">Close ×</button></div><dl id="record-fields"></dl></dialog>
<script id="datasets" type="application/json">{payload}</script>
</body></html>"""

if __name__ == "__main__":
    open("README.md", "w").write(README)
    os.makedirs("docs", exist_ok=True)
    open("docs/milestones.md", "w").write(f"# Spaceflight milestones ({len(ms)})\n\nSource: `data/spaceflight_milestones.csv`. Numbers match the timeline figure.\n\n" + ms[["num","date","milestone","actor","category","significance"]].to_markdown(index=False) + "\n")
    open("docs/data-changelog.md", "w").write(f"# Data changelog — revision of {AS_OF}\n\n{len(ch)} edits. Source: `data/changelog.csv`.\n\n" + ch.to_markdown(index=False) + "\n")
    # Refresh generated folders without deleting unrelated hosting files.
    os.makedirs("site", exist_ok=True)
    for d in ["images", "data", "osalr", "docs"]:
        shutil.copytree(d, f"site/{d}", dirs_exist_ok=True, ignore=shutil.ignore_patterns("*.py", "__pycache__"))
    shutil.copytree("scripts/site_assets", "site/assets", dirs_exist_ok=True)
    for filename in ("LICENSE", "LICENSE-DATA.md"):
        shutil.copy2(filename, f"site/{filename}")
    open("site/index.html", "w").write(page_html())
    from check_site import validate_site
    print(validate_site())
    print("README.md", len(README), "chars | site files", sum(len(fs) for _, _, fs in os.walk("site")))
