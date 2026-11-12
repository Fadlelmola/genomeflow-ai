import runpy
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.genomeflow.preflight import allow_qc

CLEAR = ("Synthetic", "Synthetic origin confirmed", "Approved", "None confirmed")


class StopRun(Exception):
    pass


class PreflightTests(unittest.TestCase):
    def test_clear(self):
        self.assertTrue(allow_qc(MagicMock(), CLEAR))

    def test_block_before_processing(self):
        for mode, entry, processor in [
            ("Project upload", "app.py", "src.genomeflow.batch.stage"),
            ("Single sample", "src/genomeflow/single.py", "src.genomeflow.fastq.analyze"),
        ]:
            for index, value in enumerate(("Human or mixed", "Unresolved", "Restricted", "Present or unknown")):
                with self.subTest(mode=mode, value=value):
                    settings = list(CLEAR)
                    settings[index] = value
                    ui = MagicMock()
                    ui.radio.return_value = mode
                    ui.selectbox.side_effect = settings if mode == "Project upload" else ["RNA-seq", *settings]
                    ui.stop.side_effect = StopRun
                    with patch.dict("sys.modules", streamlit=ui), patch(processor) as process:
                        with self.assertRaises(StopRun):
                            runpy.run_path(str(Path(__file__).resolve().parents[1] / entry))
                        process.assert_not_called()
                        self.assertIn("HOLD", ui.warning.call_args.args[0])
