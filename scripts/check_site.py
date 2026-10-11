"""Validate generated assets, local links and complete dataset/database coverage."""
import csv
import json
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

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_payload = False

    def handle_data(self, data):
        if self.in_payload:
            self.payload.append(data)


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
    site = root / "site"
    page = Page()
    page.feed((site / "index.html").read_text(encoding="utf-8"))
    errors = [f"Duplicate element ID: {identifier}" for identifier in page.duplicates]
    for link in page.links:
        url = urlsplit(link)
        if url.scheme or url.netloc:
            continue
        target = site / unquote(url.path) if url.path else site / "index.html"
        if not target.is_file():
            errors.append(f"Missing local resource: {link}")
        elif url.fragment and target == site / "index.html" and unquote(url.fragment) not in page.ids:
            errors.append(f"Missing anchor: {link}")

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
        copy = site / relative
        if not copy.is_file() or copy.read_bytes() != source.read_bytes():
            errors.append(f"Download differs from source CSV: {relative}")
        if relative not in page.links:
            errors.append(f"CSV is absent from downloads: {relative}")
    for folder in ("images", "docs", "osalr"):
        for source in (root / folder).iterdir():
            if not source.is_file() or source.suffix == ".py":
                continue
            relative = source.relative_to(root)
            target = site / relative
            if not target.is_file() or target.read_bytes() != source.read_bytes():
                errors.append(f"Missing or outdated published file: {relative}")
    for source in (root / "scripts" / "site_assets").iterdir():
        target = site / "assets" / source.name
        if not target.is_file() or target.read_bytes() != source.read_bytes():
            errors.append(f"Missing or outdated site asset: {source.name}")

    _, failures = read_csv(root / "data" / "failures.csv")
    _, master = read_csv(root / "osalr" / "osalr_master.csv")
    failure_by_name = {row["name"]: row for row in failures}
    if len(failure_by_name) != len(failures) or len({row["record_id"] for row in master}) != len(master):
        errors.append("Duplicate failure name or OSALR record ID")
    if len(master) != len(failures):
        errors.append("OSALR master and curated failures have different record counts")
    for row in master:
        original = failure_by_name.get(row["name"])
        if original is None or any(row.get(key) != value for key, value in original.items()):
            errors.append(f"OSALR master differs from curated failure: {row['name']}")
    _, cadence = read_csv(root / "data" / "launch_cadence.csv")
    for row in cadence:
        if int(row["global_orbital_attempts"]) != int(row["spacex_all_vehicles"]) + int(row["other"]):
            errors.append(f"Launch counts do not add up for {row['year']}")

    with sqlite3.connect(f"file:{site / 'osalr' / 'osalr.db'}?mode=ro", uri=True) as database:
        if database.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            errors.append("Database integrity check failed")
        if database.execute("PRAGMA foreign_key_check").fetchall():
            errors.append("Database contains invalid foreign keys")
        for table in ("events", "references_tbl", "fix_verifications"):
            ids = {row[0] for row in database.execute(f"SELECT record_id FROM {table}")}
            if ids != {row["record_id"] for row in master}:
                errors.append(f"Database {table} does not cover all master records")
            if database.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] != len(master):
                errors.append(f"Duplicate or missing database rows in {table}")
        modes = set(database.execute("SELECT record_id, code FROM event_modes"))
        expected_modes = {(row["record_id"], code.strip()) for row in master for code in row["failure_mode_codes"].split(";") if code.strip()}
        if modes != expected_modes:
            errors.append("Database failure-mode assignments differ from master")
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
        for row in master:
            actual = records.get(row["record_id"], {})
            for field, value in row.items():
                if field in ("root_cause_category", "failure_mode_codes"):
                    continue  # Stored as controlled event_modes, checked above.
                stored = actual.get(column_map.get(field, field))
                if ("" if stored is None else str(stored)) != value:
                    errors.append(f"Database differs from master: {row['record_id']} / {field}")
    if errors:
        raise ValueError("Site validation failed:\n" + "\n".join(errors))
    return f"Validated {len(datasets)} datasets / {sum(len(d['rows']) for d in datasets)} rows, {len(page.links)} links, all published assets and {len(master)} database events."


if __name__ == "__main__":
    print(validate_site())
