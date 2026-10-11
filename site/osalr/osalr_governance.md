# How a shared failure database could work

OSALR (Open Spaceflight Anomaly & Lesson Repository) is a working database today: 45 failures from 1957 to October 2026, coded and checked for whether the fix held. This page sketches how it could grow into something the industry shares and maintains together.

## Why it's needed

Of the 45 failures in the database, 40 can be checked for repeats, and in **30 of those 40 (75%)** the same kind of failure also hit another flight. Propulsion failures alone have hit 12 different organizations. Uncommanded engine shutdown has hit 6 organizations in 3 countries over 56 years, from the Soviet N1 in 1969 to Japan's H3 in 2025.

The newest failures are the hardest to learn from. 7 of the 8 failures logged in 2026 have no public cause (`UNK-UNDISC`), so nobody outside the operator can learn from them. When each organization keeps its failure history to itself, others end up relearning the same lessons. OSALR turns "has this happened before, to anyone?" into a one-line query.

## Models it borrows from

- **Aviation: ICAO ADREP and the EU's ECCAIRS.** ICAO member states file accident and incident reports into a common repository coded with one shared taxonomy. ECCAIRS gives it a common data model, so a fault reported in France can be searched in Japan. Aviation is as safe as it is largely because reporting is required, coded and shared. OSALR copies this model directly.
- **Software security: CVE and CWE.** Every known vulnerability gets a stable public ID (CVE-YYYY-NNNNN), and CWE is the taxonomy of weakness types underneath. A vendor can say "we were hit by CWE-120" without publishing exploit code. OSALR's `record_id` (OSALR-YYYY-NNNN) works like a CVE ID, and its `failure_mode_code` list works like CWE.

## Who runs it

**A neutral steward.** A vendor-neutral body maintains the taxonomy and decides what goes in the public and restricted tiers. It could be an IAASS- or COSPAR-style international association, or an ISO working group. The steward assigns record IDs and reviews submissions for proprietary detail. Its job is to collect lessons, not to assign blame.

**Members agree to file.** Agencies, launch companies, primes and insurers commit to filing a record within a fixed window after their mishap board closes, the same duty to report that makes aviation's system work. Filing your lessons is what earns you access to everyone else's.

## Two access tiers

| Tier | What it holds | Who can see it |
|---|---|---|
| **Public** | Failure-mode code, flight phase, factual cause summary, lesson learned, type of fix, whether the fix held, source | Anyone |
| **Restricted** | Proprietary design and engineering detail, exact part specs, internal test data | Members only |

The public tier is enough to answer "has this happened before, and did the fix hold?" The restricted tier protects commercial and export-controlled (ITAR) detail. **Proprietary concerns never block a submission:** the public lesson can always be separated from the private detail, the same way a CVE can be filed without the exploit.

## How a record gets in

1. **Submit.** After its mishap board closes, the organization fills in `osalr_intake_template.csv`.
2. **Review.** The steward moves proprietary or ITAR-controlled detail into the restricted tier. The public record keeps the failure mode, phase, lesson and fix outcome.
3. **Code.** The steward assigns a `record_id` and checks the `failure_mode_code` values against the taxonomy.
4. **Publish.** The public record goes live. Records are append-only: corrections and later fix updates are added as new rows and never overwrite old ones, just as a CVE is never silently edited.
5. **Follow up.** The fix outcome is revisited as later flights add evidence. "Too recent to assess" and "Not yet re-flown" eventually become Yes, Partially or No.

## How it could grow

1. **Seed (done).** 45 events from 1957 to October 2026, coded and checked, ship today as `osalr.db`. It's a working reference implementation you can query now.
2. **Convene.** A small founding group ratifies the taxonomy and the filing window. One national agency, two launch companies and one insurer would be enough to start.
3. **Federate.** Members map their internal anomaly systems to the OSALR schema. Nobody has to rebuild their tooling; they export to a common format.
4. **Require.** As in aviation, the long-term goal is to tie filing to launch licensing, so sharing the public lesson becomes a condition of flight.

---

*Reference implementation: `osalr.db` (SQLite, 45 events from 24 organizations, 36 failure-mode codes), `failure_mode_taxonomy.csv`, `failure_db_schema.json` and `osalr_intake_template.csv`. Every query in `query_demos.md` runs against the shipped database.*
