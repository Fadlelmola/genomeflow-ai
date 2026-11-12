"""Assay-scoped QC tools. The model selects a tool; Python computes every value."""
import os

TOOLS = ("read_count", "q30", "readiness")


def lookup(rows, tool, minimum=None):
    reads = sum(int(row["reads"]) for row in rows)
    bases = sum(int(row["bases"]) for row in rows)
    high = sum(int(row["q30_bases"]) for row in rows)
    if not rows or bases <= 0:
        raise ValueError("No analyzed bases in this selection.")
    if tool == "read_count":
        return f"{len(rows)} sample(s), {reads:,} reads."
    if tool == "q30":
        return f"{high:,} of {bases:,} bases reached Q30 ({100*high/bases:.4f}%)."
    if tool != "readiness":
        raise ValueError("Unknown QC tool.")
    if minimum is None:
        return "Review required. No minimum Q30 percentage was supplied."
    if not 0 <= minimum <= 100:
        raise ValueError("Minimum Q30 percentage must be between 0 and 100.")
    hits = sum(100*int(r["q30_bases"]) >= minimum*int(r["bases"]) for r in rows)
    return f"{hits} of {len(rows)} samples meet the Q30 criterion of {minimum:g}%. This evaluates Q30 only."


class UnsupportedQuestion(ValueError):
    """The question has no matching QC tool."""


def select_tool(question):
    from openai import OpenAI
    client = OpenAI(timeout=12, max_retries=2)
    response = client.responses.create(model=os.environ["OPENAI_MODEL"],
        instructions="Choose the QC tool requested. Return exactly read_count, q30, or readiness. Return unsupported for any other request.",
        input=question, max_output_tokens=64, store=False)
    name = response.output_text.strip()
    if name == "unsupported":
        raise UnsupportedQuestion("Please ask about read counts, Q30 or a Q30 threshold.")
    if name not in TOOLS:
        raise ValueError("Choose a supported question about reads, Q30 or readiness.")
    return name
