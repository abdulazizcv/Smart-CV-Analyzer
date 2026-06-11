"""
Migration: adds all new columns to cv_results.
Run once with: python migrate.py
"""
import sqlite3

DB_PATH = "cv_analysis.db"

NEW_COLUMNS = [
    ("original_filename",   "TEXT"),
    ("summary",             "TEXT"),
    ("ats_explanation",     "TEXT"),
    ("found_skills",        "TEXT"),
    ("missing_skills",      "TEXT"),
    ("recommended_roles",   "TEXT"),
    ("matched_job_skills",  "TEXT"),
    ("missing_job_skills",  "TEXT"),
    ("recommendations",     "TEXT"),
    ("job_description",     "TEXT"),
    ("required_skills",     "TEXT"),
]

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(cv_results)")
existing = {row[1] for row in cursor.fetchall()}

added = []
for col_name, col_type in NEW_COLUMNS:
    if col_name not in existing:
        cursor.execute(f"ALTER TABLE cv_results ADD COLUMN {col_name} {col_type}")
        added.append(col_name)

conn.commit()
conn.close()

if added:
    print(f"✅ Migration complete. Added columns: {', '.join(added)}")
else:
    print("ℹ️  All columns already exist — nothing to do.")