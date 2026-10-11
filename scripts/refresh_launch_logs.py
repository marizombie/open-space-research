"""refresh_launch_logs.py — re-derives launch counts and the failure ledger from Wikipedia's launch logs.

Writes to build/refresh/ only; it never edits data/. Compare the output with data/launch_cadence.csv and
data/launch_failures_2025_2026.csv, then copy accepted changes in by hand and log them in data/changelog.csv.

  python scripts/refresh_launch_logs.py                       # annual totals 2010..last year + current year to date
  python scripts/refresh_launch_logs.py --offline             # use build/cache only (no network)
  python scripts/refresh_launch_logs.py --first 2015 --current 2026

Counting rules (match the published data):
  * annual totals = the 'total', 'success', 'failed' and 'partial' fields of the "<year> in spaceflight" summary
    (includes Starship flight tests)
  * current year  = TLS-RL rows with a filled outcome in the orbital section, plus Starship rows in the suborbital section
  * failure ledger = orbital-section rows where any payload outcome is "Launch failure"
Wikipedia text is CC BY-SA 4.0; derived files inherit that licence.
"""
import argparse, datetime as dt, json, os, re, time, urllib.error, urllib.parse, urllib.request
from collections import Counter
import pandas as pd

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
CACHE, OUT = os.path.join(ROOT, "build", "cache"), os.path.join(ROOT, "build", "refresh")
API = "https://en.wikipedia.org/w/api.php"
UA = "open-spaceflight-research/1.0 (data refresh script" + (f"; {os.environ['OSR_CONTACT']}" if os.environ.get("OSR_CONTACT") else "") + ")"
BLOC = {"France": "Europe", "Italy": "Europe", "Germany": "Europe"}  # grouping used in data/launch_share.csv
MONTHS = {m: i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August",
                                      "September", "October", "November", "December"], 1)}
COUNTRY = {"USA": "USA", "CHN": "China", "China": "China", "RUS": "Russia", "IND": "India", "JPN": "Japan",
           "FRA": "France", "ITA": "Italy", "DEU": "Germany", "GER": "Germany", "KOR": "South Korea",
           "IRN": "Iran", "Iran": "Iran", "ISR": "Israel", "NZL": "New Zealand", "AUS": "Australia", "BRA": "Brazil"}


def slug(title): return re.sub(r"[^A-Za-z0-9]+", "_", title).strip("_")


def wikitext(title, offline=False):
    """Wikitext of a page, cached in build/cache. Returns None if the page does not exist."""
    path = os.path.join(CACHE, slug(title) + ".wikitext")
    if os.path.exists(path): return open(path, encoding="utf-8").read()
    if offline: return None
    q = urllib.parse.urlencode({"action": "parse", "page": title, "prop": "wikitext", "format": "json", "redirects": 1})
    for attempt in range(5):
        try:
            req = urllib.request.Request(f"{API}?{q}", headers={"User-Agent": UA})
            d = json.load(urllib.request.urlopen(req, timeout=40)); break
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 4: raise
            time.sleep(8 * (attempt + 1))
    time.sleep(2)  # be polite to the API
    if "parse" not in d: return None
    os.makedirs(CACHE, exist_ok=True)
    txt = d["parse"]["wikitext"]["*"]; open(path, "w", encoding="utf-8").write(txt); return txt


def clean(s):
    s = re.sub(r"<ref[^>]*?/>", "", s); s = re.sub(r"<ref[^>]*>.*?</ref>", "", s, flags=re.S)
    s = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", s); return re.sub(r"<!--.*?-->", "", s, flags=re.S)


def field(block, name):
    m = re.search(r"\n\|\s*" + name + r"\s*=\s*(.*?)(?=\n\|[a-zA-Z\-]+\s*=|\n\|payload|\Z)", block, re.S) \
        or re.search(r"\|\s*" + name + r"\s*=\s*([^\n|]*)", block)
    if not m: return ""
    s = re.sub(r"\{\{#invoke:flag\|icon\|[^}]*\}\}", "", clean(m.group(1))); s = re.sub(r"\{\{!\}\}", "|", s)
    return re.sub(r"\s+", " ", s).strip()


def launch_rows(wtxt):
    """All TLS-RL launch rows on a list page, flagged orbital/suborbital section."""
    cut = re.search(r"==\s*Suborbital", wtxt); cpos = cut.start() if cut else len(wtxt)
    rows, pos = [], 0
    for part in re.split(r"(?=\{\{TLS-RL)", wtxt):
        start = pos; pos += len(part)
        if not part.startswith("{{TLS-RL"): continue
        flag = re.search(r"\|rocket\s*=\s*\{\{#invoke:flag\|icon\|([^}]+)\}\}", part)
        rows.append(dict(orbital=start < cpos, date=field(part, "date"), rocket=field(part, "rocket"),
                         flight=re.sub(r"\|.*", "", field(part, "flight")).strip().strip('"'),
                         remarks=re.sub(r"\|payload.*", "", field(part, "remarks"), flags=re.S).strip()[:300],
                         country=COUNTRY.get(flag.group(1).strip(), flag.group(1).strip()) if flag else "",
                         outcomes=[o.strip() for o in re.findall(r"\|\s*outcome\s*=\s*([^\n|}<]+)", part)]))
    return rows


def list_pages(year, offline):
    q = [f"List of spaceflight launches in {a} {year}" for a in ("January–March", "April–June", "July–September", "October–December")]
    pages = [wikitext(t, offline) for t in q]
    if all(p is None for p in pages):  # some years use half-year pages
        pages = [wikitext(f"List of spaceflight launches in {a} {year}", offline) for a in ("January–June", "July–December")]
    return [p for p in pages if p]


def rowdate(r, year):
    m = re.match(r"(\d{1,2})\s+([A-Z][a-z]+)", r["date"])
    return dt.date(year, MONTHS[m.group(2)], int(m.group(1))) if m and m.group(2) in MONTHS else None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--first", type=int, default=2010); ap.add_argument("--current", type=int, default=dt.date.today().year)
    ap.add_argument("--ledger-from", type=int, default=2025); ap.add_argument("--offline", action="store_true")
    a = ap.parse_args()
    if a.first >= a.current or a.ledger_from > a.current:
        ap.error("--first must precede --current, and --ledger-from must not exceed --current")

    def infobox(w, name):
        m = re.search(r"\|\s*" + name + r"\s*=\s*(\d*)", w or "", re.I)
        return (int(m.group(1)) if m.group(1) else 0) if m else None  # a present but blank field means zero

    totals = []
    for y in range(a.first, a.current):
        w = wikitext(f"{y} in spaceflight", a.offline)
        totals.append(dict(year=y, global_orbital_attempts=infobox(w, "total"), successes=infobox(w, "success"),
                           failures=infobox(w, "failed"), partial_failures=infobox(w, "partial")))

    led, spx, ytd = [], {}, Counter()
    available_years = set()
    for y in range(a.ledger_from, a.current + 1):
        pages = list_pages(y, a.offline)
        if not pages:
            print(f"No launch-log data available for {y}; counts are unknown, not zero.")
            continue
        available_years.add(y)
        rows = [r for p in pages for r in launch_rows(p)]
        done = [r for r in rows if any(r["outcomes"])] if y == a.current else rows
        spx[y] = sum(1 for r in done if re.search(r"Falcon 9|Falcon Heavy|Starship", r["rocket"]))
        if y == a.current:
            for r in done:
                if r["orbital"] or "Starship" in r["rocket"]: ytd[BLOC.get(r["country"], r["country"]) or "?"] += 1
        for r in rows:
            if r["orbital"] and any("launch failure" in o.lower() for o in r["outcomes"]):
                d = rowdate(r, y)
                led.append(dict(date=d.isoformat() if d else r["date"], vehicle=re.sub(r"\s*\(.*", "", r["rocket"]).strip(),
                                flight=r["flight"], country=r["country"], outcome="Launch failure", remarks=r["remarks"]))

    if not available_years:
        print("No refresh files written. Populate build/cache by running without --offline first.")
        return
    os.makedirs(OUT, exist_ok=True)
    current_total = sum(ytd.values()) if a.current in available_years else None
    t = pd.DataFrame(totals); t.loc[len(t)] = [a.current, current_total, None, None, None]
    t["spacex_all_vehicles"] = t.year.map(spx); t["partial_year"] = t.year == a.current
    t.to_csv(os.path.join(OUT, "launch_cadence_refresh.csv"), index=False)
    pd.DataFrame(sorted(ytd.items(), key=lambda kv: -kv[1]), columns=["country", f"launches_{a.current}_ytd"]).to_csv(os.path.join(OUT, "launch_share_refresh.csv"), index=False)
    L = pd.DataFrame(led, columns=["date", "vehicle", "flight", "country", "outcome", "remarks"]).sort_values("date"); L.to_csv(os.path.join(OUT, "launch_failures_refresh.csv"), index=False)

    cur = pd.read_csv(os.path.join(ROOT, "data", "launch_cadence.csv"))
    cmp_ = t.merge(cur[["year", "global_orbital_attempts", "spacex_all_vehicles"]], on="year", how="left", suffixes=("_new", "_data"))
    diff = cmp_[(cmp_.global_orbital_attempts_new != cmp_.global_orbital_attempts_data) |
                (cmp_.spacex_all_vehicles_new.notna() & (cmp_.spacex_all_vehicles_new != cmp_.spacex_all_vehicles_data))]
    failures = sum(L.date.astype(str).str.startswith(str(a.current))) if a.current in available_years else "unknown"
    print(f"{a.current} to date: {current_total if current_total is not None else 'unknown'} launches, SpaceX {spx.get(a.current, 'unknown')}, failures {failures}")
    print("years that differ from data/launch_cadence.csv:", "none" if diff.empty else "\n" + diff.to_string(index=False))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
