# OSALR — query demonstrations
Database: `osalr.db` (45 events, 24 organizations, 36 codes). Data current to 9 Oct 2026. Every table below is the literal output of the SQL shown.

## Q1. One failure mode, many organizations — uncommanded engine shutdown (`PROP-SHUT`)
```sql
SELECT e.record_id, e.event_name, e.year, o.org_name, o.bloc
FROM events e JOIN event_modes m USING(record_id) JOIN organizations o USING(org_id)
WHERE m.code = 'PROP-SHUT' ORDER BY e.year;
```
| record_id       | event_name              |   year | org_name   | bloc        |
|:----------------|:------------------------|-------:|:-----------|:------------|
| OSALR-1969-0001 | N1 (all 4 flights)      |   1969 | USSR       | USSR/Russia |
| OSALR-2021-0001 | Astra Rocket 3.3 LV0006 |   2021 | Astra      | USA         |
| OSALR-2021-0002 | Firefly Alpha Flight 1  |   2021 | Firefly    | USA         |
| OSALR-2022-0001 | Astra TROPICS-1         |   2022 | Astra      | USA         |
| OSALR-2023-0001 | ABL RS1 Flight 1        |   2023 | ABL Space  | USA         |
| OSALR-2023-0004 | Starship IFT-1          |   2023 | SpaceX     | USA         |
| OSALR-2025-0006 | Starship Flight 8       |   2025 | SpaceX     | USA         |
| OSALR-2025-0002 | H3 (nav satellite)      |   2025 | JAXA       | Japan       |

6 organizations in 3 blocs over 56 years.

## Q2. Vehicles lost on the ground during fuelled tests or pre-launch
```sql
SELECT e.record_id, e.event_name, e.event_date, o.org_name, e.phase, e.loss_severity
FROM events e JOIN organizations o USING(org_id)
WHERE e.phase IN ('Ground test','Pre-launch','Pre-launch (fueling)') ORDER BY e.event_date;
```
| record_id       | event_name                              | event_date   | org_name    | phase                | loss_severity                             |
|:----------------|:----------------------------------------|:-------------|:------------|:---------------------|:------------------------------------------|
| OSALR-1960-0001 | Nedelin catastrophe                     | 1960-10-24   | USSR        | Pre-launch           | Pad catastrophe                           |
| OSALR-1967-0001 | Apollo 1 fire                           | 1967-01-27   | USA (NASA)  | Ground test          | Crew lost                                 |
| OSALR-2016-0001 | Falcon 9 AMOS-6                         | 2016-09-01   | SpaceX      | Pre-launch (fueling) | Vehicle+payload lost                      |
| OSALR-2025-0004 | SpaceX Starship Ship 36 (static fire)   | 2025-06-18   | SpaceX      | Ground test          | Vehicle lost (test-stand)                 |
| OSALR-2026-0007 | New Glenn static-fire explosion (LC-36) | 2026-05-28   | Blue Origin | Ground test          | Vehicle lost; launch pad severely damaged |

## Q3. Did the fix hold? — PSLV third stage
```sql
SELECT e.record_id, e.event_name, e.event_date, f.did_fix_hold, r.reference_type
FROM events e JOIN fix_verifications f USING(record_id) JOIN references_tbl r USING(record_id)
WHERE e.vehicle LIKE 'PSLV%' ORDER BY e.event_date;
```
| record_id       | event_name        | event_date   | did_fix_hold     | reference_type                                 |
|:----------------|:------------------|:-------------|:-----------------|:-----------------------------------------------|
| OSALR-2025-0003 | PSLV-C61 / EOS-09 | 2025-05-18   | No               | Agency inquiry (publication status unverified) |
| OSALR-2026-0001 | PSLV-C62 / EOS-N1 | 2026-01-12   | Not yet re-flown | Agency inquiry (not published)                 |

PSLV-C62 failed in the same third-stage phase as PSLV-C61 eight months earlier. The C62 Failure Analysis Committee report (13 Jun 2026) was not released.

## Q4. Which 2026 failures have a public cause?
```sql
SELECT e.record_id, e.event_name, o.org_name, r.reference_type
FROM events e JOIN organizations o USING(org_id) JOIN references_tbl r USING(record_id)
WHERE e.year = 2026 ORDER BY e.event_date;
```
| record_id       | event_name                              | org_name        | reference_type                     |
|:----------------|:----------------------------------------|:----------------|:-----------------------------------|
| OSALR-2026-0001 | PSLV-C62 / EOS-N1                       | ISRO            | Agency inquiry (not published)     |
| OSALR-2026-0002 | Long March 3B/E (Shijian 32)            | CASC            | No public report                   |
| OSALR-2026-0003 | Ceres-2 Y1 (maiden flight)              | Galactic Energy | No public report                   |
| OSALR-2026-0004 | KAIROS Flight 3                         | Space One       | No public report                   |
| OSALR-2026-0005 | Tianlong-3 Y1 (maiden flight)           | Space Pioneer   | No public report                   |
| OSALR-2026-0006 | New Glenn NG-3 (BlueBird 7)             | Blue Origin     | Regulator-overseen (not published) |
| OSALR-2026-0007 | New Glenn static-fire explosion (LC-36) | Blue Origin     | Company statement                  |
| OSALR-2026-0008 | Long March 7A (ChinaSat-4B)             | CASC            | No public report                   |

7 of 8 2026 events have no public cause statement; the exception is Blue Origin's statement on the LC-36 ground-test explosion.
Caveat: 2026 rows cover every failure that year, while pre-2026 rows are a curated set of notable events, often selected because a report exists. The two groups are not a like-for-like comparison.

## Q5. Fix-verification status across all 45 events
```sql
SELECT did_fix_hold, COUNT(*) n FROM fix_verifications GROUP BY did_fix_hold ORDER BY n DESC;
```
| did_fix_hold               |   n |
|:---------------------------|----:|
| Yes                        |  18 |
| Not yet re-flown           |   8 |
| No                         |   6 |
| Partially                  |   4 |
| N/A (vehicle retired)      |   4 |
| By design (iterative test) |   3 |
| Too recent to assess       |   2 |
