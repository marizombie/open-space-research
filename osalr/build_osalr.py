#!/usr/bin/env python3
"""build_osalr.py — rebuilds osalr.db from two CSVs. Run: python osalr/build_osalr.py
Inputs : osalr_master.csv (one row per event, all fields + record_id, bloc, failure_mode_codes)
         failure_mode_taxonomy.csv (controlled codes: classes + leaf modes)
         osalr_schema.sql
Output : osalr.db with organizations, failure_modes, events, event_modes, references_tbl, fix_verifications
"""
import sqlite3, os, pandas as pd
os.chdir(os.path.dirname(os.path.abspath(__file__)))  # works from any directory

DB = "osalr.db"
ev  = pd.read_csv("osalr_master.csv")
tax = pd.read_csv("failure_mode_taxonomy.csv")
if os.path.exists(DB): os.remove(DB)
con = sqlite3.connect(DB); con.execute("PRAGMA foreign_keys=ON"); cur = con.cursor()
cur.executescript(open("osalr_schema.sql").read())

orgs = ev[["org_country","bloc"]].drop_duplicates("org_country").reset_index(drop=True)
for i,r in orgs.iterrows():
    cur.execute("INSERT INTO organizations(org_id,org_name,bloc) VALUES(?,?,?)",(i+1,r.org_country,r.bloc))
oid = {r.org_country:i+1 for i,r in orgs.iterrows()}

cls, leaf = tax[tax.code==tax.parent_class], tax[tax.code!=tax.parent_class]
for _,r in pd.concat([cls,leaf]).iterrows():
    cur.execute("INSERT INTO failure_modes VALUES(?,?,?,?,?)",(r.code,r.parent_class,r.class_name,r.mode_name,r.definition))

def s(x): return None if pd.isna(x) else str(x)
for _,r in ev.iterrows():
    cur.execute("""INSERT INTO events(record_id,event_name,event_date,year,org_id,vehicle,phase,mission_type,crewed,
                   loss_severity,fatalities,cause_detail,lesson_learned,access_tier) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (r.record_id,r["name"],s(r.date),int(r.year),oid[r.org_country],s(r.vehicle),s(r.phase),s(r.mission_type),s(r.crewed),
         s(r.loss_severity),int(r.fatalities) if pd.notna(r.fatalities) else None,s(r.cause_detail),s(r.lesson_learned),"public"))
    for c in str(r.failure_mode_codes).split(";"):
        if c.strip(): cur.execute("INSERT INTO event_modes VALUES(?,?)",(r.record_id,c.strip()))
    cur.execute("INSERT INTO references_tbl(record_id,primary_reference,reference_type,investigation_body) VALUES(?,?,?,?)",
                (r.record_id,s(r.primary_reference),s(r.reference_type),s(r.investigation_body)))
    cur.execute("""INSERT INTO fix_verifications(record_id,corrective_action,did_fix_hold,fix_hold_evidence,root_cause_recurred,logged_at)
                   VALUES(?,?,?,?,?,?)""",(r.record_id,s(r.corrective_action),s(r.did_fix_hold),s(r.fix_hold_evidence),s(r.root_cause_recurred),"2026-10-09"))
con.commit()
bad = cur.execute("PRAGMA foreign_key_check").fetchall()
counts = {t:cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in
          ["organizations","failure_modes","events","event_modes","references_tbl","fix_verifications"]}
con.close()
assert not bad, bad
print("built", DB, counts)
