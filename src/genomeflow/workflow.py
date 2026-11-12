"""Synthetic intake and QC prototype. Scores and limits are demonstration fixtures."""
import sqlite3

ASSAYS = ("WES", "WGS", "RNA-Seq")
LIMIT = 80


def register(db, sample, assay, consent, total, passed):
    if type(total) is not int or type(passed) is not int or not 0 <= passed <= total or not 1 <= total <= 10**12:
        raise ValueError("Enter a positive total and a passing count between zero and the total.")
    score = 100 * passed / total
    if not sample.startswith("SYN-") or len(sample) < 5 or assay not in ASSAYS:
        raise ValueError("Use a SYN- identifier and a supported assay.")
    if consent not in ("Research", "Missing", "Other"):
        raise ValueError("Invalid consent category or synthetic score.")
    events = ["Registered"]
    if consent != "Research":
        events.append("Consent hold")
    else:
        events.append("Consent verified")
        events.append("Ready for simulation" if 100 * passed >= LIMIT * total else "QC hold")
    with db:
        db.execute("CREATE TABLE IF NOT EXISTS samples (id TEXT PRIMARY KEY, assay TEXT, consent TEXT, score INTEGER, status TEXT)")
        db.execute("CREATE TABLE IF NOT EXISTS events (sample TEXT, step INTEGER, detail TEXT, PRIMARY KEY(sample,step))")
        db.execute("CREATE TABLE IF NOT EXISTS qc_counts (sample TEXT PRIMARY KEY, total INTEGER, passed INTEGER)")
        db.execute("INSERT INTO samples VALUES (?,?,?,?,?)", (sample, assay, consent, score, events[-1]))
        db.execute("INSERT INTO qc_counts VALUES (?,?,?)", (sample, total, passed))
        db.executemany("INSERT INTO events VALUES (?,?,?)", [(sample,i,event) for i,event in enumerate(events,1)])
    return events[-1]
