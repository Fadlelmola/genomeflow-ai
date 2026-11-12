import csv
import io
import json
import sqlite3
import tarfile
import tempfile
import zlib
from contextlib import closing
from pathlib import Path

import streamlit as st
from src.genomeflow.preflight import controls, allow_qc
from src.genomeflow.batch import run_batch, stage

st.title("GenomeFlow: AI Multi-Agent System")
mode = st.radio("Workflow", ["Project upload", "Single sample", "QC review"], horizontal=True)
if mode == "QC review":
    from src.genomeflow.review import show
    show()
    st.stop()
if mode == "Single sample":
    from runpy import run_path
    run_path(str(Path(__file__).parent / "src" / "genomeflow" / "single.py"))
    st.stop()

with st.form("project"):
    project = st.text_input("Project ID")
    description = st.text_area("Project description")
    metadata = st.file_uploader("Additional project metadata (optional CSV or JSON)", type=["csv", "json"])
    settings = controls(st)
    st.caption("For each assay, upload its archive with samplesheet.csv, or select the FASTQ files and sample sheet together.")
    groups = {assay: st.file_uploader(assay, accept_multiple_files=True, key=assay)
              for assay in ["RNA-seq", "Exome", "WGS"]}
    submitted = st.form_submit_button("Analyze project")
if submitted:
    st.session_state.pop("report", None)
    try:
        if not allow_qc(st, settings):
            st.stop()
        if not project.strip() or not any(groups.values()):
            raise ValueError("Enter a project ID, confirm research use, and select sequencing files.")
        project = project.strip()
        with closing(sqlite3.connect("genomeflow.sqlite")) as db:
            db.execute("CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, description TEXT, scope TEXT, metadata_name TEXT, metadata BLOB, results TEXT)")
            if db.execute("SELECT 1 FROM projects WHERE id=?", (project,)).fetchone():
                raise ValueError("Project ID already exists.")
            rows = []
            for assay, uploads in groups.items():
                if uploads:
                    with st.spinner(f"Analyzing {assay}"), tempfile.TemporaryDirectory() as tmp:
                        files = stage(Path(tmp), ((u.name, u) for u in uploads))
                        rows.extend(run_batch(files, assay))
            with db:
                db.execute("INSERT INTO projects VALUES (?,?,?,?,?,?)",
                           (project, description, "Synthetic local research", metadata.name if metadata else None,
                            metadata.getvalue() if metadata else None, json.dumps(rows)))
        st.session_state.report = (project, rows)
    except (ValueError, OSError, EOFError, sqlite3.Error, tarfile.TarError, zlib.error, csv.Error) as error:
        st.error(str(error))
if "report" in st.session_state:
    project, rows = st.session_state.report
    display = [{"project": project, **{k:v for k,v in r.items() if k != "sample_metadata"},
                **{f"sheet_{k}":v for k,v in r["sample_metadata"].items()}} for r in rows]
    st.success(f"{project}: completed QC for {len(rows)} samples.")
    st.dataframe(display)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(dict.fromkeys(k for r in display for k in r)))
    writer.writeheader()
    writer.writerows(display)
    st.download_button("Download QC results", output.getvalue(), "genomeflow_qc.csv", "text/csv")
