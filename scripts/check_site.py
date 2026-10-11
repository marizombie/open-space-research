"""Validate generated assets, local links and complete dataset/database coverage."""
import csv
import json
import re
import sqlite3
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = set()
        self.duplicates = set()
        self.payload = []
        self.in_payload = False
        self.h1 = 0
        self.title = ""
        self.in_title = False
        self.description = ""
        self.structured = []
        self.in_structured = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        identifier = attrs.get("id")
        if identifier:
            if identifier in self.ids:
                self.duplicates.add(identifier)
            self.ids.add(identifier)
        for key in ("src", "href"):
            if attrs.get(key):
                self.links.append(attrs[key])
        if tag == "script" and identifier == "datasets":
            self.in_payload = True
        if tag == "script" and attrs.get("type") == "application/ld+json":
            self.in_structured = True
            self.structured.append("")
        if tag == "h1":
            self.h1 += 1
        if tag == "title":
            self.in_title = True
        if tag == "meta" and attrs.get("name") == "description":
            self.description = attrs.get("content", "")

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_payload = self.in_structured = False
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_payload:
            self.payload.append(data)
        if self.in_structured:
            self.structured[-1] += data
        if self.in_title:
            self.title += data


def read_csv(filename):
    with filename.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError(f"Missing or duplicate column names: {filename}")
        if any(None in row or any(value is None for value in row.values()) for row in rows):
            raise ValueError(f"Malformed CSV row: {filename}")
        return reader.fieldnames, rows


def validate_site(root=ROOT):
    root = Path(root).resolve()
    site = root / "site"
    pages = {}
    errors = []
    for filename in site.rglob("*.html"):
        parsed = Page()
        parsed.feed(filename.read_text(encoding="utf-8"))
        pages[filename.resolve()] = parsed
        errors.extend(f"Duplicate element ID in {filename.relative_to(site)}: {identifier}" for identifier in parsed.duplicates)
    page = pages[(site / "index.html").resolve()]
    titles = {}
    for filename, parsed in pages.items():
        name = filename.relative_to(site)
        if parsed.h1 != 1:
            errors.append(f"Expected one <h1> in {name}, found {parsed.h1}")
        if not parsed.title.strip() or not parsed.description.strip():
            errors.append(f"Missing <title> or meta description in {name}")
        titles.setdefault(parsed.title.strip(), []).append(str(name))
        for block in parsed.structured:
            try:
                json.loads(block)
            except ValueError:
                errors.append(f"Invalid JSON-LD in {name}")
    errors.extend(f"Duplicate <title> on {', '.join(names)}" for names in titles.values() if len(names) > 1)
    if not (site / "robots.txt").is_file():
        errors.append("Missing robots.txt")
    sitemap = site / "sitemap.xml"
    if sitemap.is_file():
        listed = {urlsplit(loc).path.lstrip("/") for loc in re.findall(r"<loc>([^<]+)</loc>", sitemap.read_text(encoding="utf-8"))}
        published = {"" if f.parent == site else f.parent.relative_to(site).as_posix() + "/" for f in pages}
        errors.extend(f"Page missing from sitemap.xml: /{path}" for path in sorted(published - listed))
        errors.extend(f"sitemap.xml lists a page that does not exist: /{path}" for path in sorted(listed - published))
    for filename, parsed in pages.items():
        for link in parsed.links:
            url = urlsplit(link)
            if url.scheme or url.netloc:
                continue
            target = (site / unquote(url.path.lstrip("/"))) if url.path.startswith("/") else (filename.parent / unquote(url.path)) if url.path else filename
            if target.is_dir():
                target = target / "index.html"
            target = target.resolve()
            if not target.is_file():
                errors.append(f"Missing local resource in {filename.relative_to(site)}: {link}")
            elif url.fragment and target in pages and unquote(url.fragment) not in pages[target].ids:
                errors.append(f"Missing anchor in {filename.relative_to(site)}: {link}")
            if target.suffix in (".csv", ".db", ".sqlite", ".sqlite3"):
                errors.append(f"Raw data download link remains: {link}")
    for artifact in site.rglob("*"):
        if artifact.is_file() and artifact.suffix in (".csv", ".db", ".sqlite", ".sqlite3"):
            errors.append(f"Raw data artifact is publicly exposed: {artifact.relative_to(site)}")

    datasets = json.loads("".join(page.payload))
    sources = {source.relative_to(root).as_posix(): source for folder in ("data", "osalr") for source in (root / folder).glob("*.csv")}
    published = {dataset["path"]: dataset for dataset in datasets}
    if len(published) != len(datasets) or len({dataset["id"] for dataset in datasets}) != len(datasets):
        errors.append("Duplicate dataset ID or source path")
    if sources.keys() != published.keys():
        errors.append("Explorer does not include exactly every source CSV")
    for relative, source in sources.items():
        columns, rows = read_csv(source)
        dataset = published.get(relative)
        if dataset and (dataset["columns"] != columns or dataset["rows"] != rows):
            errors.append(f"Explorer differs from source CSV: {relative}")
        if dataset:
            destination = site / dataset["url"] / "index.html"
            if dataset["url"] not in page.links:
                errors.append(f"Dataset page is absent from the catalog: {relative}")
            detail = pages.get(destination.resolve())
            if detail is None:
                errors.append(f"Missing dataset page: {dataset['url']}")
            elif json.loads("".join(detail.payload)) != [dataset]:
                errors.append(f"Dataset page differs from source: {relative}")
    for folder in ("images", "docs", "osalr"):
        for source in (root / folder).iterdir():
            if not source.is_file() or source.suffix in (".py", ".csv", ".db", ".sqlite", ".sqlite3"):
                continue
            relative = source.relative_to(root)
            target = site / relative
            if not target.is_file() or target.read_bytes() != source.read_bytes():
                errors.append(f"Missing or outdated published file: {relative}")
    for source in (root / "scripts" / "site_assets").iterdir():
        target = site / "assets" / source.name
        if not target.is_file() or target.read_bytes() != source.read_bytes():
            errors.append(f"Missing or outdated site asset: {source.name}")

    # data/failures.csv is the only failures table; osalr.db is built from it.
    _, failures = read_csv(root / "data" / "failures.csv")
    if len({row["name"] for row in failures}) != len(failures) or len({row["record_id"] for row in failures}) != len(failures):
        errors.append("Duplicate failure name or OSALR record ID")
    _, cadence = read_csv(root / "data" / "launch_cadence.csv")
    for row in cadence:
        if int(row["global_orbital_attempts"]) != int(row["spacex_all_vehicles"]) + int(row["other"]):
            errors.append(f"Launch counts do not add up for {row['year']}")

    with sqlite3.connect(f"file:{root / 'osalr' / 'osalr.db'}?mode=ro", uri=True) as database:
        if database.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            errors.append("Database integrity check failed")
        if database.execute("PRAGMA foreign_key_check").fetchall():
            errors.append("Database contains invalid foreign keys")
        for table in ("events", "references_tbl", "fix_verifications"):
            ids = {row[0] for row in database.execute(f"SELECT record_id FROM {table}")}
            if ids != {row["record_id"] for row in failures}:
                errors.append(f"Database {table} does not cover every row of data/failures.csv")
            if database.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] != len(failures):
                errors.append(f"Duplicate or missing database rows in {table}")
        modes = set(database.execute("SELECT record_id, code FROM event_modes"))
        expected_modes = {(row["record_id"], code.strip()) for row in failures for code in row["failure_mode_codes"].split(";") if code.strip()}
        if modes != expected_modes:
            errors.append("Database failure-mode assignments differ from data/failures.csv")
        database.row_factory = sqlite3.Row
        records = {row["record_id"]: dict(row) for row in database.execute("""
            SELECT e.*, o.org_name, o.bloc, r.primary_reference, r.reference_type,
                   r.investigation_body, f.corrective_action, f.did_fix_hold,
                   f.fix_hold_evidence, f.root_cause_recurred
            FROM events e JOIN organizations o USING(org_id)
            JOIN references_tbl r USING(record_id)
            JOIN fix_verifications f USING(record_id)
        """)}
        column_map = {"name": "event_name", "date": "event_date", "org_country": "org_name"}
        for row in failures:
            actual = records.get(row["record_id"], {})
            for field, value in row.items():
                if field in ("root_cause_category", "failure_mode_codes"):
                    continue  # Stored as controlled event_modes, checked above.
                stored = actual.get(column_map.get(field, field))
                if ("" if stored is None else str(stored)) != value:
                    errors.append(f"Database differs from data/failures.csv: {row['record_id']} / {field}")
    if errors:
        raise ValueError("Site validation failed:\n" + "\n".join(errors))
    return f"Validated {len(datasets)} datasets / {sum(len(d['rows']) for d in datasets)} rows, {sum(len(parsed.links) for parsed in pages.values())} links across {len(pages)} pages, all published assets and {len(failures)} database events."


if __name__ == "__main__":
    print(validate_site())
