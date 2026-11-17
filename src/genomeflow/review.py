import csv
import io
import os

import streamlit as st
from src.genomeflow.agent import TOOLS, UnsupportedQuestion, lookup, select_tool


def show():
    st.header("Review sequencing quality")
    st.caption("Upload the GenomeFlow QC export. Choose one assay or sample for this review.")
    file = st.file_uploader("GenomeFlow QC CSV", type="csv")
    if not file:
        return
    try:
        rows = list(csv.DictReader(io.StringIO(file.getvalue().decode("utf-8-sig"))))
        if not rows or not {"project","assay","sample","reads","bases","q30_bases"}.issubset(rows[0]):
            raise ValueError("Choose a GenomeFlow QC export.")
        for row in rows:
            if any(not row.get(key) for key in ("project", "assay", "sample")):
                raise ValueError("Every row needs a project, assay and sample ID.")
            for key in ("reads", "bases", "q30_bases"):
                row[key] = int(row[key])
            if row["reads"] <= 0 or row["bases"] <= 0 or not 0 <= row["q30_bases"] <= row["bases"]:
                raise ValueError("Read/base counts must be positive and Q30 bases must fit within total bases.")
        project = st.selectbox("Project", sorted({r["project"] for r in rows}))
        rows = [r for r in rows if r["project"] == project]
        assay = st.selectbox("Review assay", sorted({r["assay"] for r in rows}))
        rows = [r for r in rows if r["assay"] == assay]
        sample = st.selectbox("Sample", [None] + sorted({r["sample"] for r in rows}), format_func=lambda x:x or "All samples")
        if sample is not None:
            rows = [r for r in rows if r["sample"] == sample]
        minimum = st.number_input("Project minimum Q30 (%) if specified", value=None, min_value=0., max_value=100.)
        labels = {"read_count": "Read count", "q30": "Base quality (Q30)", "readiness": "Compare with your Q30 threshold"}
        tool = st.selectbox("What would you like to check?", TOOLS, format_func=lambda value: labels[value])
        question = st.text_input("Optional AI question (question text only)")
        if st.button("Review selection"):
            if question.strip():
                cache = st.session_state.setdefault("qc_routes", {})
                key = (os.getenv("OPENAI_MODEL"), question.strip())
                try:
                    if not os.getenv("OPENAI_API_KEY") or not key[0]:
                        raise RuntimeError("API configuration missing")
                    if key not in cache:
                        with st.spinner("Selecting a QC tool..."):
                            cache[key] = select_tool(key[1])
                    tool = cache[key]
                    st.caption("API-selected tool: " + tool)
                except UnsupportedQuestion as error:
                    st.info(str(error))
                    return
                except Exception as error:
                    if not os.getenv("OPENAI_API_KEY") or not os.getenv("OPENAI_MODEL"):
                        st.warning("AI routing is not configured. Your selected local check will run instead. Local QC does not require an API key.")
                    else:
                        st.warning("AI routing could not complete. Your selected local check will run instead. Try again later or continue locally.")
            st.write(lookup(rows, tool, minimum))
    except (ValueError, TypeError, csv.Error) as error:
        st.error(str(error))
