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

st.set_page_config(page_title="GenomeFlow", page_icon="🧬", layout="wide")
# Reserve the content area before the footer so early st.stop() calls keep the notice visible.
content = st.container()
st.divider()
st.caption("© 2026 Faisal M. Fadlelmola. All rights reserved.")
with content:
    st.markdown("""<style>
    .block-container {max-width:1100px;padding-top:2rem}
    [data-testid="stForm"] {border-radius:16px;padding:24px}
    .stButton button[kind="primary"],.stFormSubmitButton button {background:#116c78;color:white;border:0}
    .gf-banner {background:linear-gradient(115deg,#103845,#126b76);color:white;border-radius:18px;padding:28px 32px;margin-bottom:22px}
    .gf-banner h1 {color:white;margin:0;font-size:34px}.gf-banner p {color:#e0f1f2;margin:8px 0}
    @media (max-width: 640px) {
      .block-container {padding-left:1rem;padding-right:1rem}
      [data-testid="stForm"] {padding:16px}
      .gf-banner {padding:20px 16px}
      .gf-banner h1 {font-size:28px}
    }
    </style>""", unsafe_allow_html=True)
    st.markdown("""<div class="gf-banner"><h1>🧬 GenomeFlow</h1><p>AI Multi-Agent System · Research sequencing workflows</p><p>Register your project. Confirm permissions. Calculate sequencing quality.</p></div>""", unsafe_allow_html=True)
    st.caption("Synthetic research demonstration · No patient names or identifiers · Live AI routing tested on selected synthetic examples")
    mode = st.radio("Choose your task", ["Register and analyze", "Review QC results"], horizontal=True)
    if mode == "Review QC results":
        from src.genomeflow.review import show
        show()
        st.stop()

    st.subheader("1. Choose sequencing methods")
    assays = st.multiselect("Methods in this project", ["RNA-seq", "Exome", "WGS"], default=["RNA-seq"])
    st.caption("Choose one method or several. Only the selected upload areas will appear.")
    with st.expander("Try the supplied example"):
        st.write("Use project ID DEMO-UI-001 and requesting PI Demo PI. Select RNA-seq and upload example.fastq with samplesheet.csv from the examples folder. Sample DEMO-01 is already listed in the sheet.")
        st.download_button("Download example sample sheet", (Path(__file__).parent / "examples/samplesheet.csv").read_bytes(), "samplesheet.csv", "text/csv")
        st.download_button("Download example FASTQ", (Path(__file__).parent / "examples/example.fastq").read_bytes(), "example.fastq", "text/plain")
    with st.form("project"):
        st.subheader("2. Register your project")
        left, right = st.columns(2)
        with left:
            project = st.text_input("Project ID *", placeholder="e.g. GF-2026-001")
        with right:
            requesting_pi = st.text_input("Requesting PI or senior scientist *", placeholder="Name of the research requester")
        st.caption("Sample IDs come from your sample sheet. Use one row per sample. Do not enter participant names.")
        description = st.text_area("Project description", placeholder="Research purpose and sequencing scope", height=80)
        metadata = st.file_uploader("Additional project metadata (optional)", type=["csv", "json"], help="This field is separate from the required sample sheet for each method.")
        st.subheader("3. Confirm consent and data governance")
        st.caption("Confirm the status of the received materials. This demo uses declarations and accepts synthetic data only. Do not upload signed consent documents or patient information.")
        settings = controls(st)
        st.subheader("4. Upload sequencing files")
        groups = {}
        for assay in assays:
            st.markdown(f"**{assay}**")
            groups[assay] = st.file_uploader(f"{assay}: FASTQ files and one sample sheet *", accept_multiple_files=True, key=assay,
                help="Select FASTQ files and samplesheet.csv together, or upload a .tar.gz archive containing both. Required columns: sample, fastq_1. Add fastq_2 for paired reads.")
        st.caption("After you start, the workflow checks declarations, validates files, calculates QC and displays the results. Missing approval keeps processing on hold.")
        submitted = st.form_submit_button("Check permissions and run QC", use_container_width=True)
    if submitted:
        st.session_state.pop("report", None)
        try:
            if not allow_qc(st, settings):
                st.stop()
            if not project.strip() or not requesting_pi.strip() or not groups or any(not uploads for uploads in groups.values()):
                raise ValueError("Enter a project ID and requesting PI, and upload files for every selected method.")
            project = project.strip()
            with closing(sqlite3.connect("genomeflow.sqlite")) as db:
                db.execute("CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, description TEXT, scope TEXT, metadata_name TEXT, metadata BLOB, results TEXT)")
                if db.execute("SELECT 1 FROM projects WHERE id=?", (project,)).fetchone():
                    raise ValueError("This project ID already has results. Use a new project ID for another run.")
                rows = []
                for assay, uploads in groups.items():
                    if uploads:
                        with st.spinner(f"Analyzing {assay}"), tempfile.TemporaryDirectory() as tmp:
                            files = stage(Path(tmp), ((u.name, u) for u in uploads))
                            rows.extend(run_batch(files, assay))
                with db:
                    db.execute("INSERT INTO projects VALUES (?,?,?,?,?,?)",
                               (project, "Requesting PI: " + requesting_pi.strip() + "\n" + description, "Synthetic local research", metadata.name if metadata else None,
                                metadata.getvalue() if metadata else None, json.dumps(rows)))
            st.session_state.report = (project, rows)
        except (ValueError, OSError, EOFError, sqlite3.Error, tarfile.TarError, zlib.error, csv.Error) as error:
            st.error(str(error))
    if "report" in st.session_state:
        project, rows = st.session_state.report
        display = [{"project": project, **{k:v for k,v in r.items() if k != "sample_metadata"},
                    **{f"sheet_{k}":v for k,v in r["sample_metadata"].items()}} for r in rows]
        st.success(f"{project}: completed QC for {len(rows)} samples.")
        a, b, c = st.columns(3)
        a.metric("Samples processed", len(rows))
        b.metric("Total reads", f"{sum(r['reads'] for r in rows):,}")
        bases = sum(r['bases'] for r in rows)
        c.metric("Bases at Q30 or higher", f"{100 * sum(r['q30_bases'] for r in rows) / bases:.2f}%")
        st.caption("Q30 measures base-call quality. These metrics alone do not establish overall sample suitability.")
        labels = {"assay":"Method", "sample":"Sample ID", "reads":"Reads", "bases":"Bases", "q30_pct":"Q30 (%)", "gc_pct":"GC (%)", "n_bases":"N bases"}
        st.dataframe([{label:r[key] for key,label in labels.items()} for r in rows], use_container_width=True, hide_index=True)
        with st.expander("Full results and sample metadata"):
            st.dataframe(display, use_container_width=True)
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(dict.fromkeys(k for r in display for k in r)))
        writer.writeheader()
        writer.writerows(display)
        st.download_button("Download QC results", output.getvalue(), "genomeflow_qc.csv", "text/csv")
