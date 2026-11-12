import csv
import shutil
import tarfile
from pathlib import Path

from src.genomeflow.fastq import analyze

FASTQ = (".fastq", ".fq", ".fastq.gz", ".fq.gz")


def stage(root, uploads):
    """Copy only FASTQs and sample sheets, without extracting archive paths."""
    files = {}

    def copy(name, source):
        key = Path(name).name
        if key in files:
            raise ValueError(f"Duplicate filename in assay: {key}")
        target = root / str(len(files))
        with target.open("wb") as out:
            shutil.copyfileobj(source, out)
        files[key] = target

    for name, stream in uploads:
        stream.seek(0)
        if name.lower().endswith((".tar.gz", ".tgz")):
            with tarfile.open(fileobj=stream, mode="r|gz") as archive:
                for member in archive:
                    if member.isfile() and (member.name.lower().endswith(FASTQ) or Path(member.name).name == "samplesheet.csv"):
                        with archive.extractfile(member) as source:
                            copy(member.name, source)
        elif name.lower().endswith(FASTQ + (".csv",)):
            copy(name, stream)
        else:
            raise ValueError(f"Unsupported input: {name}")
    return files


def run_batch(files, assay):
    sheets = [p for name, p in files.items() if name.lower().endswith(".csv")]
    if len(sheets) != 1:
        raise ValueError(f"{assay} requires one sample sheet.")
    with sheets[0].open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not {"sample", "fastq_1"}.issubset(reader.fieldnames or []):
            raise ValueError("Sample sheet requires sample and fastq_1 columns. Use fastq_2 for paired reads.")
        rows = list(reader)
    used = set()
    samples = set()
    results = []
    for row in rows:
        sample = (row["sample"] or "").strip()
        names = [(row["fastq_1"] or "").strip()]
        if row.get("fastq_2"):
            names.append(row["fastq_2"].strip())
        if not sample or sample in samples:
            raise ValueError(f"Missing or repeated sample ID in {assay}: {sample}")
        samples.add(sample)
        for name in names:
            if name in used or name not in files or not name.lower().endswith(FASTQ):
                raise ValueError(f"{sample}: missing or repeated FASTQ: {name}")
            used.add(name)
        reads, bases, q30, gc, n = analyze([files[name] for name in names])
        results.append(dict(assay=assay, sample=sample, reads=reads, bases=bases, q30_bases=q30,
                            q30_pct=round(100*q30/bases, 4), gc_pct=round(100*gc/bases, 4),
                            n_bases=n, sample_metadata=row))
    if not results or used != {k for k in files if k.lower().endswith(FASTQ)}:
        raise ValueError("Empty sheet or uploaded FASTQs missing from the sample sheet.")
    return results
