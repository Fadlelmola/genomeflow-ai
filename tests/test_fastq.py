import tempfile
import unittest
from pathlib import Path

from src.genomeflow.batch import run_batch, stage

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


class ProjectUploadTests(unittest.TestCase):
    def test_rna_only_example(self):
        with tempfile.TemporaryDirectory() as folder:
            with (EXAMPLES / "example.fastq").open("rb") as reads, (EXAMPLES / "samplesheet.csv").open("rb") as sheet:
                inputs = stage(Path(folder), [("example.fastq", reads), ("samplesheet.csv", sheet)])
            row, = run_batch(inputs, "RNA-seq")
        self.assertEqual((row["sample"], row["reads"], row["bases"]), ("DEMO-01", 2, 8))
        self.assertEqual((row["q30_pct"], row["gc_pct"], row["n_bases"]), (75, 50, 2))
