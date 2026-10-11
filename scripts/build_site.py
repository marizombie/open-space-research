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
ledger = pd.read_csv("data/launch_failures_2025_2026.csv"); om = f
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
    n_codes=len(tax), wiki_fail25=cy(2025, "failures") + cy(2025, "partial_failures"),
)
# Share of launches that fully succeeded, per year.
rate = lambda y: 100 * cy(y, "successes") / cy(y, "global_orbital_attempts")
full_years = c[~c.partial_year]
rate_lo, rate_hi = (100 * full_years.successes / full_years.global_orbital_attempts).agg(["min", "max"])
worst = full_years.loc[(full_years.successes / full_years.global_orbital_attempts).nsmallest(2).index, "year"].sort_values().tolist()
# Falcon 9 launches in 2025 and 2026 to date, from organizations.csv ("165 (Falcon 9)", "110 Falcon 9 + 3 Falcon Heavy").
f9_row = o[o.flagship_vehicle.str.startswith("Falcon 9")].iloc[0]
f9_flights = sum(int(re.search(r"(\d+)\s*\(?Falcon 9", str(f9_row[col])).group(1)) for col in ("orbital_launches_2025", "orbital_launches_2026_ytd"))
f9_failed = int(ledger.vehicle.str.startswith("Falcon 9").sum())
lc = pd.read_csv("data/launch_costs.csv").set_index("vehicle").cost_per_kg_usd
shuttle_kg, f9r_kg, fh_kg = lc["Space Shuttle"], lc["Falcon 9 (reused)"], lc["Falcon Heavy"]
held = f[f.did_fix_hold == "Yes"]
sh = pd.read_csv("data/launch_share.csv").set_index("bloc")
share = lambda col: 100 * (col["USA"] + col["China"]) / col.sum()
fail26 = ", ".join(f"{k} {v}" for k, v in ledger[ledger.date >= "2026"].country.value_counts().items())

SECTIONS = [
("About this data", f"""
Everything here is current to **{AS_OF}**. Launch counts come from one source, Wikipedia's *"<year> in spaceflight"* summaries for 2010–2025 and the 2026 launch log through 7 October, and they include Starship flight tests. Other trackers count 2025 a little differently: SpaceNews has 324 launches, BryceTech 325, Jonathan McDowell 329 and Wikipedia 330.
A few kinds of numbers are estimates, and they are labelled as estimates wherever they appear: price per kg, technology readiness levels (TRL), China's space budget and private-company finances. Everything else is a dated event with a source. Every edit in this revision is listed in [docs/data-changelog.md](docs/data-changelog.md).
"""),
("1 · Spaceflight firsts, 1232 to 2026", f"""
`spaceflight_milestones.csv` lists **{N['n_ms']} firsts**: USA {int((ms.actor.str.startswith('USA')).sum())}, USSR/Russia {int((ms.actor.str.startswith('USSR')|ms.actor.str.startswith('Russia')).sum())}, China {int(ms.actor.str.startswith('China').sum())}, and the rest from Europe, Japan, India and international projects.
- **Before Sputnik:** Jin-dynasty rocket weapons (c.1232; historians still argue about the exact devices, and the Wan Hu legend is left out), Tsiolkovsky's rocket equation (1903), Goddard's liquid-fuel rocket (1926), GIRD-09, the first Soviet liquid-fuel rocket (1933), the V-2 reaching space (1944), the first Soviet A-4 launches at Kapustin Yar (1947), Bumper 5, the first two-stage rocket to reach space (1949), and Dezik and Tsygan, the first dogs to fly to space and come back (1951).
- **2026 so far:** Artemis II (1–11 Apr) took four people around the Moon, the first crew beyond low Earth orbit since 1972 and the farthest anyone has been from Earth. China caught a Long March 10B booster at sea (10 Jul), becoming the second country to recover an orbital booster. Isar's Spectrum became the first rocket to reach orbit from Western Europe (5 Sep), and Starship Flight 14 (28 Sep) was Starship's first orbital and first commercial flight.
""", ["milestones_timeline"]),
("2 · Launches: more of them, and more of them work", f"""
- World orbital launch attempts rose from **{N['c2010']} in 2010 to {N['c2025']} in 2025**, 4.5× in 15 years. SpaceX flew **{N['s2025']} ({round(100*N['s2025']/N['c2025'])}%)** of the 2025 launches.
- **2026 to 7 Oct: {N['c2026']} launches**, {N['s2026']} of them by SpaceX. The USA ({sh.at['USA', '2026 YTD']}) and China ({sh.at['China', '2026 YTD']}) flew {share(sh['2026 YTD']):.0f}% of them, about the same share as in 2025 ({share(sh['2025']):.0f}%).
- **Reliability held up under all that extra traffic.** {rate(2010):.1f}% of launches fully succeeded in 2010, {rate(2025):.1f}% in 2025 and {rate(2026):.1f}% so far in 2026. Every year since 2010 landed between {rate_lo:.0f}% and {rate_hi:.0f}%; the worst were {worst[0]} and {worst[1]}. Failures did go up in number, from {cy(2010, 'failures') + cy(2010, 'partial_failures')} in 2010 to {N['wiki_fail25']} in 2025, but far more slowly than launches.
- **Falcon 9 flew {f9_flights} times in 2025 and 2026 to date, and {"none of those launches failed" if f9_failed == 0 else f"{f9_failed} failed"}.** Its two losses in our catalogue, CRS-7 (2015) and AMOS-6 (2016), both led to fixes that held.
- 2026 has had **{N['ledger26']} launch failures** so far: {fail26}. All {N['ledger25'] + N['ledger26']} failures from 2025 and 2026 are listed in `launch_failures_2025_2026.csv`. That list follows Wikipedia's orbital launch tables, so it leaves out Starship test flights; Wikipedia's yearly failure count ({N['wiki_fail25']} for 2025) includes them.
""", ["launch_cadence", "reliability"]),
("3 · What went wrong: {n} failures since 1957".format(n=N['n_fail']), f"""
`failures.csv` holds **{N['n_fail']} failures**: {N['n_fail'] - N['n2026']} well-known events from 1957 to 2025, plus every orbital launch failure of 2026 and the New Glenn explosion on the pad. Five of them killed {N['deaths']} people: the Nedelin disaster (1960, 78), Apollo 1 (1967, 3), Soyuz 1 (1967, 1), Challenger (1986, 7) and Columbia (2003, 7). No crew has been lost since Columbia. When Soyuz MS-10 failed on the way up in 2018, its escape system brought both astronauts home.
- **Engines and propellant systems cause the most failures** ({N['prop']} of {N['n_fail']}). The {N['undiscl']} events with no public cause are all from 2026.
- **Did the fix work?** For {N['fix_yes']} failures, yes: the vehicle flew again without the same problem. For {N['fix_no']}, no: the rocket failed again later (Vega, Astra, Firefly twice, Starship Flight 7→8 and PSLV-C61→C62), and in the Starship and PSLV cases it failed the same way. Another {N['notyet']} are waiting for a return to flight, so it's too early to tell.
- **New Glenn (28 May 2026)** exploded during a static fire and badly damaged Launch Complex 36. Blue Origin traced it (5 Aug) to a BE-4 main oxygen valve. That makes three rockets lost on the ground in ten years, after AMOS-6 (2016) and Starship Ship 36 (2025).
""", ["failures_overview"]),
("4 · What we learned", f"""
Most failures teach something specific, and {N['fix_yes']} of those lessons have held up on later flights. Six of them:
- **Apollo 1 (1967):** no more pure-oxygen cabins on the pad, and a hatch that opens outward in seconds. No Apollo cabin fire happened again.
- **Mars Climate Orbiter (1999):** one system of units across every contractor, enforced through interface documents. No mission in our catalogue has been lost to a units mix-up since.
- **Columbia (2003):** treat "in-family" anomalies like foam strikes as real risks, and inspect the heat shield in orbit. The Shuttle flew 22 more missions without a loss before it retired in 2011.
- **Falcon 1 Flight 3 (2008):** allow for leftover engine thrust when timing stage separation. Flight 4 reached orbit, the first privately built liquid-fuel rocket to do so.
- **Soyuz MS-10 (2018):** a sensor bent during assembly caused the failure, and the abort system did its job. Assembly checks changed and the problem hasn't come back.
- **H3 (2023 and 2025):** JAXA fixed a second-stage ignition fault after the first flight and an upper-stage problem in 2025. H3 has since flown successfully, twice in 2026 alone.

The harder lesson is that the same kinds of failure keep turning up at different companies. In **{N['rec_yes']} of the {N['rec_known']} failures we can check ({round(100*N['rec_yes']/N['rec_known'])}%)**, the same kind of failure also hit another flight, before or after. Uncommanded engine shutdown alone has hit 6 organizations in 3 countries since 1969, from the Soviet N1 to Japan's H3.
- **2026 has a disclosure problem.** {N['n2026_nocause']} of the {N['n2026']} failures logged this year have no public cause, so nobody outside the operator can learn from them. PSLV-C62 failed in the same third-stage phase as PSLV-C61 eight months earlier, and ISRO has not published the C62 inquiry report it completed on 13 Jun 2026.
- **OSALR (Open Spaceflight Anomaly & Lesson Repository)** is a small SQLite database built to answer two questions fast: has this failure mode happened before, and did the fix hold? It holds the same {N['n_fail']} events from {N['orgs']} organizations, tagged with {N['n_codes']} failure-mode codes in 8 classes (`UNK` covers undisclosed or undetermined causes), plus a source and a fix outcome for each. `build_osalr.py` rebuilds it from `failures.csv` on every build, so the CSV is the only thing you ever edit. `query_demos.md` has five example queries, and `osalr_governance.md` sketches how a shared industry version could work.
""", ["learning_loop"]),
("5 · Cost per kilogram", f"""
- Rough price per kg to low Earth orbit (*estimates*): Space Shuttle ~${shuttle_kg:,.0f}, reused Falcon 9 ~${f9r_kg:,.0f}, Falcon Heavy ~${fh_kg:,.0f}. That's about {shuttle_kg / f9r_kg:.0f}× cheaper than the Shuttle, which was partly reusable too but expensive to refurbish between flights. Starship's ~$100/kg is a company target and hasn't been demonstrated.
- **What you buy matters as much as the rocket.** A Falcon 9 commercial launch to LEO lists at ${f9.min():,.0f}/kg. NASA's ISS cargo contract (CRS-2) works out to ${f9.max():,.0f}/kg, {f9.max()/f9.min():.0f}× more, but that price also covers the Dragon capsule and cargo services. SLS to the Moon costs about $81,481/kg per launch, not counting development.
""", ["cost_per_kg"]),
("6 · Who pays for spaceflight", f"""
- **NASA's FY2026 budget is $24.4B.** In January 2026 Congress turned down nearly all of a proposed 24% cut; the FY2027 request proposes a 23% cut again. NASA alone outspends ESA (~$8.5B, 2024), Roscosmos (~$3.4B, 2023), JAXA (~$2.1B) and ISRO (~$1.6B) combined. China publishes no figure; independent estimates put it at $14–19B.
- **Private money is concentrated in one company.** SpaceX took in about $13B of revenue in 2024 (est.). For scale, all of China's commercial launch startups together have raised about $8B in investment (est.).
""", ["funding"]),
("7 · What's still missing for crewed Mars flights", f"""
We track 12 capabilities a crewed interplanetary mission needs, and all of them sit at TRL 3–6 (*our estimates, not agency ratings*; TRL 9 means flight-proven). 2026 brought real flight evidence in two areas: super-heavy reuse (Starship reached orbit, and China recovered Long March 10B and Zhuque-3 boosters) and deep-space crew operations (Artemis II). The least mature haven't moved: deep-space radiation protection and surface habitats (TRL 3), then ISRU, Mars entry-descent-landing, nuclear propulsion and cryogenic refuelling (TRL 4). As of October 2026 nobody has reported a ship-to-ship transfer of cryogenic propellant.
""", ["tech_gaps"]),
("8 · Open work: where you can help", """
1. **Add the 8 remaining 2025 failures to OSALR:** Spectrum F1, Eris F1, Zhuque-2E Y3, Ceres-1 Y19, Kuaizhou-1A Y33, Hanbit-Nano, Simorgh and Zuljanah. They are already in `launch_failures_2025_2026.csv` and need a cause, lesson and failure-mode code.
2. **Update the 8 "not yet re-flown" records** when each vehicle flies again. Next up: PSLV-C63 (Nov 2026) and Astrobotic Griffin-1 (no earlier than Nov 2026). New Glenn has no date yet.
3. **Find cause statements** from ISRO, CASC, Space One, Space Pioneer, Galactic Energy and Blue Origin. Every `UNK-UNDISC` record that gets a cause becomes a lesson others can use.
4. **Replace estimates with primary sources:** agency-published TRLs, contract award prices (NASA and NSSL notices) for `cost_model.csv`, and official FY2026 budgets for ESA, JAXA and ISRO.
5. **Log what happens next:** Starship Flight 15, Mengzhou-1 on Long March 10A, Gaganyaan G1 (HLVM3), JAXA's MMX (20 Oct) and Starliner-1 (Dec) are all due in Q4 2026.
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
    output = "\n".join(out)
    for dataset in DATASETS:
        basename = Path(dataset["path"]).name
        output = output.replace(f"<code>{basename}</code>", f'<a href="{dataset["url"]}"><code>{basename}</code></a>')
        output = output.replace(f'href="{dataset["path"]}"', f'href="{dataset["url"]}"')
    return output

def table(df, cols, names=None, responsive=False):
    names = names or cols
    table_class = ' class="appendix-table" role="table"' if responsive else ''
    h = '<div class="table-scroll" tabindex="0" role="region" aria-label="Data table"><table' + table_class + '><thead role="rowgroup"><tr role="row">' + "".join(f'<th scope="col" role="columnheader">{H.escape(n)}</th>' for n in names) + "</tr></thead><tbody role=\"rowgroup\">"
    for _, r in df.iterrows():
        h += '<tr role="row">' + "".join(f'<td role="cell" data-label="{H.escape(n, quote=True)}">{H.escape(str(r[c])) if pd.notna(r[c]) else ""}</td>' for c, n in zip(cols, names)) + "</tr>"
    return h + "</tbody></table></div>"

CAPTIONS = {
 "milestones_timeline": "Spaceflight firsts by nation or agency. Numbers match the list in Appendix A.",
 "launch_cadence": "(a) Orbital launch attempts per year; the hatched 2026 bar runs to 7 Oct. (b) Launches by country or bloc, 2025 and 2026 to date.",
 "reliability": "(a) Share of orbital launches that fully succeeded each year; the y-axis starts at 88%. (b) Failed and partly failed launches per year.",
 "failures_overview": "(a) Main root cause of each failure. (b) Whether the fix held on later flights.",
 "learning_loop": "(a) Failures whose kind also hit another flight, by era. (b) Failure modes ranked by how many organizations they have hit.",
 "cost_per_kg": "(a) Approximate price per kg to LEO by vehicle (estimates). (b) Contract price divided by payload capacity, by contract type.",
 "funding": "(a) Government space budgets; China is an independent estimate range. (b) Private revenue and capital raised (estimates).",
 "tech_gaps": "Readiness of each capability (our estimates). Blue means new flight evidence in 2026.",
}

DATA_DESC = {
 "data/failures.csv": "45 failures from 1957 to 2026: cause, lesson learned, source, failure-mode codes, and whether the fix held",
 "data/launch_failures_2025_2026.csv": "Every orbital launch failure in 2025 and 2026 to date (Starship test flights excluded)",
 "data/launch_cadence.csv": "Orbital launches per year 2010–2026, with SpaceX share and successes, failures and partial failures (2026 partial)",
 "data/launch_share.csv": "Launches by country or bloc, 2025 and 2026 to date",
 "data/organizations.csv": "Launch providers and agencies: vehicles, launches 2025/2026, reuse status",
 "data/spaceflight_milestones.csv": "61 spaceflight firsts, from c.1232 to 2026",
 "data/launch_costs.csv": "Approximate price per kg to LEO by vehicle (estimates)",
 "data/cost_model.csv": "Contract price ÷ payload capacity, by contract type (estimates)",
 "data/funding.csv": "Government space budgets (official) and private revenue and capital raised (estimates)",
 "data/tech_gaps.csv": "Readiness of 12 capabilities for crewed interplanetary flight (our TRL estimates), with 2026 evidence",
 "data/changelog.csv": "Every edit in this revision, with its source",
 "osalr/osalr.db": "SQLite failure database (rebuild with osalr/build_osalr.py)",
 "osalr/failure_mode_taxonomy.csv": "Failure-mode codes: 8 classes and the modes under them",
 "osalr/osalr_intake_template.csv": "Fields and instructions for submitting a new failure",
 "osalr/osalr_schema.sql": "SQL schema for the SQLite database",
 "osalr/failure_db_schema.json": "Public failure-record schema",
 "osalr/osalr_governance.md": "How a shared industry version could be run: access tiers, review, fix verification",
 "osalr/query_demos.md": "Five example SQL queries and their output",
 "docs/milestones.md": "All milestones, with category and why each matters",
 "docs/data-changelog.md": "Data revision history with sources",
 "LICENSE": "MIT code licence",
 "LICENSE-DATA.md": "CC BY-SA 4.0 data, figure and text licence",
}

# Readable names for CSV columns, shown on the website. The CSV files keep their original column names.
LABELS = {
 "org_country": "Operator", "org": "Organization", "actor": "Who", "root_cause_category": "Cause",
 "cause_detail": "What happened", "cause_summary": "What happened", "lesson_learned": "Lesson learned",
 "did_fix_hold": "Did the fix hold?", "fix_hold_evidence": "How we know", "corrective_action": "Fix",
 "root_cause_recurred": "Same kind of failure on another flight?", "investigation_body": "Investigated by",
 "primary_reference": "Source", "reference_type": "Type of source", "loss_severity": "What was lost",
 "mission_phase": "Flight phase", "vehicle_or_spacecraft": "Vehicle or spacecraft", "failure_mode_codes": "Failure-mode codes",
 "record_id": "Record ID", "event_name": "Event", "num": "#", "global_orbital_attempts": "Orbital launches",
 "spacex_all_vehicles": "SpaceX launches", "other": "Everyone else", "partial_failures": "Partial failures",
 "partial_year": "Year not finished", "2026 YTD": "2026 to date", "country_bloc": "Country or bloc",
 "orbital_launches_2025": "Launches in 2025", "orbital_launches_2026_ytd": "Launches in 2026 to date",
 "leo_payload_t": "Payload to LEO (t)", "leo_kg": "Payload to LEO (kg)", "hq_location": "Headquarters",
 "cost_per_kg_usd": "Price per kg (USD)", "effective_usd_per_kg": "Price per kg (USD)",
 "published_price_musd": "Price (USD millions)", "payload_to_orbit_kg": "Payload (kg)", "destination_orbit": "Orbit",
 "annual_budget_or_revenue_busd": "Budget or revenue (USD billions)", "cumulative_private_raised_busd": "Private money raised (USD billions)",
 "current_trl": "TRL (estimate)", "readiness_label": "Readiness", "evidence_2026": "2026 evidence", "trl_basis": "Where the TRL comes from",
 "in_curated_failures_csv": "In failures.csv?", "n_events": "Events", "parent_class": "Class code", "class_name": "Class",
 "mode_name": "Failure mode", "your_entry": "Your entry", "as_of": "As of",
}

DATASET_NAMES = {
 "changelog": "Changelog", "cost_model": "Price by contract", "failures": "Failures, 1957–2026", "funding": "Funding",
 "launch_cadence": "Launches per year", "launch_costs": "Price per kg by rocket", "launch_failures_2025_2026": "Launch failures, 2025–2026",
 "launch_share": "Launches by country", "organizations": "Launch providers and agencies", "spaceflight_milestones": "Spaceflight firsts",
 "tech_gaps": "Gaps for crewed Mars flights", "failure_mode_taxonomy": "OSALR failure-mode codes",
 "osalr_intake_template": "OSALR submission form",
}

def load_datasets():
    datasets = []
    for folder in ("data", "osalr"):
        for source in sorted(Path(folder).glob("*.csv")):
            with source.open(encoding="utf-8", newline="") as stream:
                reader = csv.DictReader(stream)
                rows = list(reader)
                columns = reader.fieldnames
            datasets.append({"id": source.stem, "path": source.as_posix(),
                             "url": f"datasets/{source.stem}/",
                             "label": DATASET_NAMES.get(source.stem, source.stem.replace("_", " ").title()),
                             "description": DATA_DESC[source.as_posix()],
                             "columns": columns, "rows": rows,
                             "labels": {c: LABELS[c] for c in columns if c in LABELS}})
    return datasets

DATASETS = load_datasets()

def dataset_payload(datasets):
    # CSV text must not be able to close the script element.
    return json.dumps(datasets, ensure_ascii=False).replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")

def dataset_catalog():
    return '<div class="dataset-catalog">' + "".join(
        f'<a class="dataset-card" href="{d["url"]}"><h3>{H.escape(d["label"])}</h3>'
        f'<p>{H.escape(d["description"])}</p><span>{len(d["rows"])} records · {len(d["columns"])} fields · Open →</span></a>'
        for d in DATASETS) + '</div>'


def inventory():
    rows = []
    for p, d in DATA_DESC.items():
        n = str(len(pd.read_csv(p))) if p.endswith(".csv") else ("binary" if p.endswith(".db") else "document")
        rows.append(f"| [`{p}`]({p}) | {n} | {d} |")
    return "| File | Rows | Contents |\n|---|---:|---|\n" + "\n".join(rows)

def report_md(img):
    out = []
    for sec in SECTIONS:
        title, text = sec[0], sec[1]; figs = sec[2] if len(sec) > 2 else []
        out += [f"### {title}", text.strip(), ""]
        for fig in figs: out += [f"![{CAPTIONS[fig]}]({img(fig)})", f"<sub>{CAPTIONS[fig]}</sub>", ""]
    return "\n".join(out)

REPORT_BODY = report_md(lambda k: "images/" + k + ".png")

README = f"""# Open Spaceflight Research

Open data on orbital launches, the failures among them, and whether the fixes worked. It covers
{N['n_ms']} spaceflight firsts, {N['n_fail']} failures from 1957 to 2026 with their root causes, and a small SQLite
database (OSALR) for asking "has this failure happened before, and did the fix hold?" Data current to **{AS_OF}**.

**At a glance:** {N['c2025']} orbital launches in 2025, {rate(2025):.1f}% fully successful · {N['c2026']} in 2026 to 7 Oct ·
{N['n_fail']} failures with root cause and fix outcome · {N['fix_yes']} fixes that held · {N['orgs']} organizations in OSALR.

## Key findings
- **Rockets fly far more often, and a slightly bigger share of them work.** World orbital launches rose from {N['c2010']} in 2010 to {N['c2025']} in 2025. The share that fully succeeded stayed between {rate_lo:.0f}% and {rate_hi:.0f}% every year, and reached {rate(2026):.1f}% in 2026 so far.
- **Falcon 9 shows what a learned lesson looks like.** After losses in 2015 and 2016, both fixes held: it flew {f9_flights} times in 2025 and 2026 to date without a launch failure.
- **Most fixes hold, but the same kinds of failure keep coming back.** {N['fix_yes']} fixes held on later flights and {N['fix_no']} did not. In {N['rec_yes']} of {N['rec_known']} failures we can check, the same kind of failure also hit another flight. Uncommanded engine shutdown alone has hit 6 organizations since 1969.
- **The 2026 failures are hard to learn from.** {N['n2026_nocause']} of the {N['n2026']} failures logged this year have no public cause.
- **Launch is about {shuttle_kg / f9r_kg:.0f}× cheaper per kg than in the Shuttle era** (estimates): ~${shuttle_kg:,.0f}/kg for the Shuttle, ~${f9r_kg:,.0f} for a reused Falcon 9.
- **Crewed Mars flights are still far off.** All 12 capabilities we track sit at TRL 3–6 (our estimates). Deep-space radiation protection is the least mature.

## Repository layout
```
data/      the CSV datasets; edit these (failures.csv also feeds the database)
osalr/     OSALR database: osalr.db (built from data/failures.csv), failure-mode codes, schema, intake form, docs
images/    figures (generated by scripts/make_figures.py)
scripts/   make_figures.py, build_site.py, refresh_launch_logs.py
docs/      milestones.md, data-changelog.md (generated)
site/      static website (generated; deploy this folder)
tests/     unit tests for the refresh script and site checks
```

{inventory()}

## Report
{REPORT_BODY}

Full milestone list: [docs/milestones.md](docs/milestones.md) · Edits in this revision: [docs/data-changelog.md](docs/data-changelog.md)

## Reproduce
```bash
pip install -r requirements.txt
python scripts/build.py           # rebuild and validate the complete site
python -m unittest discover -s tests

# Or run individual steps:
python osalr/build_osalr.py        # rebuild osalr/osalr.db from data/failures.csv
python scripts/make_figures.py     # regenerate images/
python scripts/build_site.py       # regenerate README.md, docs/ and site/
python scripts/refresh_launch_logs.py   # optional: re-fetch Wikipedia launch logs and write a comparison to build/refresh/
```
`refresh_launch_logs.py` never overwrites `data/`. It writes fresh counts to `build/refresh/` so that changes can be reviewed before they are copied in.

## Deploy the website
`site/` is a complete static HTML/CSS/JavaScript site with relative links and no runtime dependencies. The data explorer embeds all {sum(1 for folder in ("data", "osalr") for source in Path(folder).glob("*.csv"))} CSV datasets at build time, so search, filters, sorting, pagination and full-record details also work offline. Each CSV has its own page under `datasets/` with search, filters, every field and full record details. Source CSVs and the SQLite database stay in the repository and are not published as downloadable files on the website.

Run `python scripts/build.py` after editing source data; it verifies every dataset, local link and database record before deployment. Deploy the generated `site/` directory with no hosting build step.

- **Cloudflare Pages:** connect the repository, set *Build command* to empty and *Build output directory* to `site`. Or deploy from the command line: `npx wrangler pages deploy site --project-name open-spaceflight-research`.
- **Vercel:** import the repository; `vercel.json` sets the output directory to `site`. Or run `npx vercel deploy --prod` from the repository root.
- **Local preview:** `python -m http.server -d site 8000`.

## Contributing
Corrections and new records are welcome. Section 8 of the report lists open work if you're looking for a place to start.
- **Add or correct a failure:** `osalr/osalr_intake_template.csv` explains every field. Add or edit the row in `data/failures.csv`, run `python scripts/build.py` to rebuild the database and site, and open a pull request. Every cause statement needs a primary source.
- **Fix other data:** edit the CSV, add a row to `data/changelog.csv` saying what changed and where it came from, then run `python scripts/build.py` and `python -m unittest discover -s tests`.
- **Commit the generated files too.** CI rebuilds everything and fails if `README.md`, `docs/` or `site/` differ from what's committed.
- Record IDs, access tiers and how fix outcomes are judged are described in [osalr/osalr_governance.md](osalr/osalr_governance.md).

## Sources and licence
- Launch counts, yearly success and failure counts, and 2025–2026 failure entries: Wikipedia, *"<year> in spaceflight"* and *"List of spaceflight launches in …"* (retrieved {AS_OF}). Historical failures cite their accident-board reports in `primary_reference`.
- Estimates (cost per kg, contract $/kg, TRL, China's budget, private funding) are labelled as estimates in the data and text.
- **Code** (`scripts/`, `osalr/build_osalr.py`): MIT licence, see [LICENSE](LICENSE).
- **Data, figures and text**: [CC BY-SA 4.0](LICENSE-DATA.md). Share-alike is required because parts are derived from Wikipedia (CC BY-SA 4.0).
"""


def explorer_html(datasets, selected="failures", dedicated=False):
    options = "".join(f'<option value="{d["id"]}"{ " selected" if d["id"] == selected else ""}>{H.escape(d["label"])} ({len(d["rows"])} rows)</option>' for d in datasets)
    heading = "Search this dataset" if dedicated else "Search the data"
    collection_count = f"{len(datasets[0]['rows'])} records · {len(datasets[0]['columns'])} fields" if dedicated else f"{len(datasets)} datasets · {sum(len(d['rows']) for d in datasets)} rows"
    fallback = 'All records are listed below.' if dedicated else 'Open any <a href="#downloads">dataset page</a> to read every record.'
    selector_hidden = ' hidden' if dedicated else ''
    all_columns = ' checked' if dedicated else ''
    page_link = '' if dedicated else '<a id="dataset-page" class="download-link">Open dataset page →</a>'
    return f"""<section id="explorer" class="explorer"><div class="section-heading"><div><p class="eyebrow">OPEN DATA</p><h2>{heading}</h2></div><span class="collection-count">{collection_count}</span></div>
<p>Search any field, filter by a column, or open a record to see everything in it, sources included. Estimates stay marked as estimates.</p>
<noscript><p class="notice">Enable JavaScript to use search and filters. {fallback}</p></noscript>
<div id="explorer-controls" hidden>
<div class="explorer-controls"><label class="dataset-control"{selector_hidden}>Dataset<select id="dataset">{options}</select></label><label class="search-control">Search every field<input id="search" type="search" placeholder="Try a vehicle, organization, year or failure mode…" autocomplete="off"></label></div>
<p id="dataset-description" class="dataset-description"></p>
<div class="filter-controls"><label>Filter field<select id="filter-field"><option value="">All fields</option></select></label><label>Value<select id="filter-value" disabled><option value="">All values</option></select></label><label>Rows per page<select id="page-size"><option value="25">25</option><option value="50">50</option><option value="100">100</option><option value="all">All</option></select></label><label class="checkbox-label"><input id="all-columns" type="checkbox"{all_columns}> Show every column</label><button id="reset-sorting" type="button" class="secondary-button" title="Restore the original record order" disabled>Reset sorting</button><button id="reset" type="button" class="secondary-button">Reset</button></div>
<div class="results-bar"><p id="results-status" role="status" aria-live="polite"></p>{page_link}</div>
<div class="table-scroll explorer-table" tabindex="0" role="region" aria-label="Dataset records; scroll horizontally to see more fields"><table id="data-table"><thead></thead><tbody></tbody></table></div>
<p id="empty-state" class="notice" hidden>No matching records. Try another search or reset the filters.</p>
<div class="pagination"><button id="previous-page" type="button" class="secondary-button">← Previous</button><span id="page-status"></span><button id="next-page" type="button" class="secondary-button">Next →</button></div>
</div></section>"""

def page_html():
    body = []
    for sec in SECTIONS:
        title, text = sec[0], sec[1]; figs = sec[2] if len(sec) > 2 else []
        blk = f"<section id='s{len(body)}'><h2>{H.escape(title)}</h2>{md_to_html(text)}"
        for fig in figs:
            blk += f'<figure><img src="images/{fig}.png" alt="{H.escape(CAPTIONS[fig])}" loading="lazy"><figcaption>{H.escape(CAPTIONS[fig])}</figcaption></figure>'
        if title.startswith("2 "):
            blk += "<h3>Who launched, 2025 and 2026 to date</h3>" + table(o, ["organization","flagship_vehicle","orbital_launches_2025","orbital_launches_2026_ytd","reuse_status","status"], ["Organization","Vehicle","2025","2026 to date","Reuse","Status"])
        if title.startswith("3 "):
            blk += "<h3>The 2026 failures</h3>" + table(f[f.year == 2026], ["date","name","org_country","root_cause_category","cause_detail","did_fix_hold"], ["Date","Event","Operator","Cause","What happened","Fix held?"])
        if title.startswith("4 "):
            blk += f"<h3>All {len(held)} fixes that held</h3>" + table(held, ["year","name","lesson_learned","fix_hold_evidence"], ["Year","Failure","Lesson","How we know it held"])
        body.append(blk + "</section>")
    resources = "".join(f"<li><a href='{p}'>{H.escape(p)}</a> — {H.escape(d)}</li>" for p, d in DATA_DESC.items() if not p.endswith((".csv", ".db")))
    body.append(f"<section id='downloads'><h2>All datasets</h2><p>Each dataset has its own page with every field and record. The CSV files and the SQLite database live in the project's repository.</p>{dataset_catalog()}</section>")
    body.append(f"<section id='resources'><h2>Documents</h2><ul>{resources}</ul></section>")
    body.append(f"<section id='milestones'><h2>Appendix A · All {len(ms)} spaceflight firsts</h2>{table(ms, ['num','date','milestone','actor'], ['#','Date','Milestone','Actor'], responsive=True)}</section>")
    body.append(f"<section id='changelog'><h2>Appendix B · What changed in this revision ({len(ch)} edits)</h2>{table(ch, ['dataset','change','source'], ['Dataset','Change','Source'], responsive=True)}</section>")
    nav = " · ".join(f"<a href='#s{i}'>{H.escape(s[0].split('·')[-1].strip())}</a>" for i, s in enumerate(SECTIONS)) + " · <a href='#downloads'>All datasets</a>"
    datasets = DATASETS
    payload = dataset_payload(datasets)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Open Spaceflight Research</title>
<meta name="description" content="Open data on orbital launches, why rockets fail, and whether the fixes worked. Data to {AS_OF}.">
<link rel="icon" href="assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="assets/site.css"><script src="assets/explorer.js" defer></script></head><body>
<a class="skip-link" href="#explorer">Skip to the data</a>
<header class="hero"><div class="hero-inner">
<div class="brand"><span class="orbit-mark" aria-hidden="true">↗</span> OPEN SPACEFLIGHT RESEARCH <span class="edition">OCTOBER 2026</span></div>
<p class="eyebrow">LAUNCHES, FAILURES AND THE FIXES THAT WORKED</p>
<h1>What spaceflight learns from its failures</h1>
<p class="intro">The world launched {N['c2025']} orbital rockets in 2025 and {cy(2025, 'successes')} of them fully worked. This site collects the ones that didn't, what broke, and whether the fix held on the next flight. All of it is open data you can search here.</p>
<p class="hero-meta">Data to {AS_OF} · launch counts to 7 October</p>
<div class="stats"><div><strong>{N['c2025']}</strong><span>Orbital launches in 2025</span></div><div><strong>{rate(2025):.1f}%</strong><span>Fully successful in 2025</span></div><div><strong>{N['n_fail']}</strong><span>Failures logged since 1957</span></div><div><strong>{N['fix_yes']}</strong><span>Fixes that held on later flights</span></div></div>
</div></header>
<main><nav class="primary-nav" aria-label="Main navigation"><a href="#explorer">Search the data</a><a href="#s0">Read the report</a><a href="#s4">What we learned</a><a href="#downloads">All datasets</a><a href="#changelog">What changed</a></nav>
{explorer_html(datasets)}
<div class="report-heading"><p class="eyebrow">REPORT</p><h2>What the data shows</h2><nav class="report-nav" aria-label="Report chapters">{nav}</nav></div>
{''.join(body)}
</main><footer><p>Open Spaceflight Research · Data to {AS_OF}</p><p>Code <a href="LICENSE">MIT</a> · Data, figures and text <a href="LICENSE-DATA.md">CC BY-SA 4.0</a> (partly derived from Wikipedia).</p></footer>
<dialog id="record-dialog" aria-labelledby="record-title"><div class="dialog-heading"><h2 id="record-title">Record details</h2><button id="close-record" type="button" class="secondary-button">Close ×</button></div><dl id="record-fields"></dl></dialog>
<script id="datasets" type="application/json">{payload}</script>
</body></html>"""

def dataset_page_html(dataset):
    title = H.escape(dataset["label"])
    description = H.escape(dataset["description"])
    fields = '<div class="table-scroll"><table class="field-table"><thead><tr><th scope="col">Field</th><th scope="col">Column name</th><th scope="col">Records with a value</th></tr></thead><tbody>' + "".join(
        f'<tr><td>{H.escape(dataset["labels"].get(field, field.replace("_", " ").title()))}</td><td><code>{H.escape(field)}</code></td><td>{sum(bool(row[field]) for row in dataset["rows"])} / {len(dataset["rows"])}</td></tr>'
        for field in dataset["columns"]) + '</tbody></table></div>'
    records = []
    for i, row in enumerate(dataset["rows"], 1):
        name = next((row[field] for field in ("name", "event_name", "milestone", "organization", "vehicle", "capability", "entity", "record_id") if row.get(field)), f"Record {i}")
        details = "".join(f'<dt>{H.escape(dataset["labels"].get(field, field.replace("_", " ").title()))}</dt><dd>{H.escape(row[field]) if row[field] else "—"}</dd>' for field in dataset["columns"])
        records.append(f'<details class="static-record"><summary>{i}. {H.escape(name)}</summary><dl>{details}</dl></details>')
    navigation = ""
    for d in DATASETS:
        active = ' aria-current="page"' if d["id"] == dataset["id"] else ''
        navigation += f'<a href="../../{d["url"]}"{active}>{H.escape(d["label"])}</a>'
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — Open Spaceflight Research</title><meta name="description" content="{description}">
<link rel="icon" href="../../assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="../../assets/site.css"><script src="../../assets/explorer.js" defer></script></head><body>
<a class="skip-link" href="#explorer">Skip to records</a>
<header class="hero dataset-hero"><div class="hero-inner"><div class="brand"><span class="orbit-mark" aria-hidden="true">↗</span> OPEN SPACEFLIGHT RESEARCH</div><p class="eyebrow">OPEN DATA</p><h1>{title}</h1><p class="intro">{description}</p><p class="hero-meta">Data to {AS_OF} · {len(dataset['rows'])} records · {len(dataset['columns'])} fields</p></div></header>
<main><nav class="primary-nav" aria-label="Dataset navigation"><a href="../../index.html">← Home</a><a href="../../index.html#downloads">All datasets</a><a href="#fields">Fields</a></nav>
{explorer_html([dataset], dataset['id'], dedicated=True)}
<section id="fields"><h2>Fields</h2><p>Source file: <code>{H.escape(dataset['path'])}</code>. Column names, blank values, estimates and source notes are kept exactly as in the file.</p>{fields}</section>
<noscript><section id="static-records"><h2>All {len(dataset['rows'])} records</h2>{''.join(records)}</section></noscript>
<section><h2>Other datasets</h2><nav class="dataset-navigation" aria-label="All dataset pages">{navigation}</nav></section>
</main><footer><p>Open Spaceflight Research · Data to {AS_OF}</p><p>Code <a href="../../LICENSE">MIT</a> · Data, figures and text <a href="../../LICENSE-DATA.md">CC BY-SA 4.0</a> (partly derived from Wikipedia).</p></footer>
<dialog id="record-dialog" aria-labelledby="record-title"><div class="dialog-heading"><h2 id="record-title">Record details</h2><button id="close-record" type="button" class="secondary-button">Close ×</button></div><dl id="record-fields"></dl></dialog>
<script id="datasets" type="application/json">{dataset_payload([dataset])}</script></body></html>"""

if __name__ == "__main__":
    open("README.md", "w").write(README)
    os.makedirs("docs", exist_ok=True)
    open("docs/milestones.md", "w").write(f"# Spaceflight milestones ({len(ms)})\n\nSource: `data/spaceflight_milestones.csv`. Numbers match the timeline figure.\n\n" + ms[["num","date","milestone","actor","category","significance"]].to_markdown(index=False) + "\n")
    open("docs/data-changelog.md", "w").write(f"# Data changelog — revision of {AS_OF}\n\n{len(ch)} edits. Source: `data/changelog.csv`.\n\n" + ch.to_markdown(index=False) + "\n")
    # Refresh generated folders without deleting unrelated hosting files.
    os.makedirs("site", exist_ok=True)
    for d in ["images", "osalr", "docs"]:
        shutil.copytree(d, f"site/{d}", dirs_exist_ok=True, ignore=shutil.ignore_patterns("*.py", "__pycache__", "*.csv", "*.db", "*.sqlite", "*.sqlite3"))
    shutil.copytree("scripts/site_assets", "site/assets", dirs_exist_ok=True)
    for filename in ("LICENSE", "LICENSE-DATA.md"):
        shutil.copy2(filename, f"site/{filename}")
    # Remove previously published raw data and database artifacts, not just their links.
    for folder in ("site/data", "site/osalr"):
        for artifact in Path(folder).glob("*"):
            if artifact.is_file() and artifact.suffix in (".csv", ".db", ".sqlite", ".sqlite3"):
                artifact.unlink()
    open("site/index.html", "w").write(page_html())
    shutil.rmtree("site/datasets", ignore_errors=True)  # drop pages for datasets that no longer exist
    for dataset in DATASETS:
        destination = Path("site") / dataset["url"]
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "index.html").write_text(dataset_page_html(dataset), encoding="utf-8")
    from check_site import validate_site
    print(validate_site())
    print("README.md", len(README), "chars | site files", sum(len(fs) for _, _, fs in os.walk("site")))
