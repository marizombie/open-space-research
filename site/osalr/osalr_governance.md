# OSALR governance one-pager
### OPEN Spaceflight Anomaly & Lesson Repository — a shared, cross-organization failure database

**The problem it solves.** Of 45 catalogued failures 1957–2026, 40 have a known recurrence status, and **30 of those 40 (75%) repeated a failure mode already seen before.** Propulsion faults hit 14 different organizations; the "uncommanded engine shutdown" mode alone recurred at 6 organizations across 3 blocs and 56 years. A newer problem: 7 of the 8 failures logged in 2026 have no public cause statement at all (`UNK-UNDISC`), so they cannot teach anyone outside the operator. The industry keeps re-teaching itself the same lessons because failure knowledge is trapped inside each organization's own history. OSALR makes *"has this mode happened before, to anyone?"* a one-line query.

---

## Precedents this model copies deliberately

- **Aviation — ICAO ADREP / EU ECCAIRS.** Every ICAO member state files accident and incident reports into a common, taxonomy-coded repository (ADREP). Europe's ECCAIRS gives it a shared data model so a Boeing fault filed in France is queryable in Japan. Aviation's safety record is what it is *because* the reporting is mandatory, coded, and shared. OSALR adopts the coded-federation model directly.
- **Cybersecurity — CVE / CWE.** CVE assigns every vulnerability a stable public ID (CVE-YYYY-NNNNN); CWE is the controlled *weakness taxonomy* underneath it. A vendor can disclose "we were hit by CWE-120" without publishing exploit code. OSALR's `record_id` (OSALR-YYYY-NNNN) mirrors CVE; its `failure_mode_code` taxonomy mirrors CWE.

---

## Governance structure

**Neutral steward.** A vendor-neutral body curates the taxonomy and mediates the public/restricted split — modeled on an **IAASS / COSPAR-style** international association or an **ISO working group**. The steward owns the taxonomy, assigns record IDs, and runs the de-identification review. It does *not* adjudicate blame — it curates lessons.

**Membership & filing commitment.** Members (agencies, primes, commercial launchers, insurers) commit to filing a record within **N months of a mishap-board closure** — the same "duty to report" that makes aviation's system work. Filing the *lesson* is the price of querying everyone else's.

## Two-tier access model

| Tier | Contains | Who sees it |
|---|---|---|
| **Public** | Failure-mode code, phase, factual cause summary, lesson learned, corrective-action *class*, fix-verification verdict, reference citation | Anyone — always shareable |
| **Restricted** | Proprietary design/engineering detail, exact part specs, internal test data | Members only, gated |

The public tier is enough to answer "has this mode happened, and did the fix hold?" — the restricted tier protects competitive and ITAR/export-controlled detail. **A submission is never blocked on proprietary concerns:** the public lesson is separable from the proprietary detail, exactly as a CVE is filable without the exploit.

## Submission & de-identification workflow

1. **Submit** — organization fills the intake template (`osalr_intake_template.csv`) after its mishap board closes.
2. **De-identify** — steward review strips proprietary/ITAR-controlled detail into the restricted tier; the public record keeps mode, phase, lesson, and fix-verification.
3. **Code** — steward assigns `record_id` and validates the `failure_mode_code`(s) against the controlled taxonomy.
4. **Publish** — public tier goes live; the record is **append-only** — corrections and later fix-verification updates are added as new rows, never overwrites (a CVE is never silently edited).
5. **Verify** — the fix-verification field is revisited as later flights accumulate evidence; "Too recent to assess" resolves to Yes / Partially / No over time.

## Adoption path

1. **Seed** (done) — 45 events (1957 – Oct 2026), coded and fix-verified, ship today as `osalr.db`. A working reference implementation, not a proposal deck.
2. **Convene** — a founding steward group (one national agency + two commercial launchers + one insurer is enough to start) ratifies the taxonomy and the filing-window commitment.
3. **Federate** — members map their internal anomaly systems to the OSALR schema; the shared model means no one rebuilds their tooling, they just export to a common format.
4. **Mandate** — as with aviation, the long-run goal is filing tied to launch licensing, so the public-safety lesson is a condition of flight, not a favor.

---

*Reference implementation: `osalr.db` (SQLite, 45 events / 24 orgs / 36 codes), `failure_mode_taxonomy.csv`, `failure_db_schema.json`, `osalr_intake_template.csv`. All queries in `query_demos.md` run against the shipped database.*
