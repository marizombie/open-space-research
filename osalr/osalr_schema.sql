CREATE TABLE organizations (
  org_id INTEGER PRIMARY KEY,
  org_name TEXT UNIQUE NOT NULL,
  bloc TEXT NOT NULL
);
CREATE TABLE failure_modes (
  code TEXT PRIMARY KEY,
  parent_class TEXT NOT NULL,
  class_name TEXT NOT NULL,
  mode_name TEXT NOT NULL,
  definition TEXT NOT NULL,
  FOREIGN KEY(parent_class) REFERENCES failure_modes(code)
);
CREATE TABLE events (
  record_id TEXT PRIMARY KEY,
  event_name TEXT NOT NULL,
  event_date TEXT,
  year INTEGER,
  org_id INTEGER,
  vehicle TEXT,
  phase TEXT,
  mission_type TEXT,
  crewed TEXT,
  loss_severity TEXT,
  fatalities INTEGER,
  cause_detail TEXT,
  lesson_learned TEXT,
  access_tier TEXT DEFAULT 'public',
  FOREIGN KEY(org_id) REFERENCES organizations(org_id)
);
CREATE TABLE event_modes (
  record_id TEXT NOT NULL,
  code TEXT NOT NULL,
  PRIMARY KEY(record_id, code),
  FOREIGN KEY(record_id) REFERENCES events(record_id),
  FOREIGN KEY(code) REFERENCES failure_modes(code)
);
CREATE TABLE references_tbl (
  ref_id INTEGER PRIMARY KEY,
  record_id TEXT NOT NULL,
  primary_reference TEXT,
  reference_type TEXT,
  investigation_body TEXT,
  FOREIGN KEY(record_id) REFERENCES events(record_id)
);
CREATE TABLE fix_verifications (
  verif_id INTEGER PRIMARY KEY AUTOINCREMENT,
  record_id TEXT NOT NULL,
  corrective_action TEXT,
  did_fix_hold TEXT,
  fix_hold_evidence TEXT,
  root_cause_recurred TEXT,
  logged_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY(record_id) REFERENCES events(record_id)
);
