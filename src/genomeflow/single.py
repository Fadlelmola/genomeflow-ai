import sqlite3
import zlib
from contextlib import closing
from pathlib import Path

import streamlit as st
from src.genomeflow.preflight import controls, allow_qc

from src.genomeflow.fastq import analyze
from src.genomeflow.workflow import ASSAYS

st.title("GenomeFlow: AI Multi-Agent System")
st.caption("Local FASTQ quality control for DNA and RNA sequencing. Standard four-line Phred+33 FASTQ, plain or gzip.")
with st.form("fastq"):
    sample = st.text_input("Sample ID")
    assay = st.selectbox("Assay", ASSAYS)
    settings = controls(st)
    first = st.text_input("FASTQ file path on this computer (single-end or R1)")
    second = st.text_input("R2 file path for paired-end reads (optional)")
    run = st.form_submit_button("Analyze FASTQ")
if run:
    if not allow_qc(st, settings):
        st.stop()
    if not sample.strip() or not first.strip():
        st.error("Enter a sample ID and FASTQ path.")
        st.stop()
    paths = [Path(value.strip().strip('"')).expanduser() for value in (first, second) if value.strip()]
    try:
        with st.spinner("Reading sequencing records..."):
            reads, bases, q30, gc, n = analyze(paths)
        with closing(sqlite3.connect("genomeflow.sqlite")) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS fastq_qc (sample TEXT PRIMARY KEY, assay TEXT, reads INTEGER, bases INTEGER, q30 INTEGER, gc INTEGER, n INTEGER)")
            db.execute("INSERT INTO fastq_qc VALUES (?,?,?,?,?,?,?)", (sample.strip(), assay, reads, bases, q30, gc, n))
        st.success("FASTQ analysis complete")
        st.metric("Bases at Q30 or higher", f"{100*q30/bases:.2f}%")
        st.write({"Reads": reads, "Bases": bases, "Bases at Q30 or higher": q30,
                  "GC (% of all bases)": round(100*gc/bases, 3), "N bases": n})
    except sqlite3.IntegrityError:
        st.error("This sample ID already has a FASTQ result.")
    except (ValueError, OSError, EOFError, zlib.error) as error:
        st.error(str(error))
