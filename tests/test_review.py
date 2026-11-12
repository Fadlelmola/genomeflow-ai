"""Exercise the actual review handler with a simulated UI and provider."""
import os
import sys
import unittest
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

DATA = b"project,assay,sample,reads,bases,q30_bases\nP,RNA-seq,S,42052,4205200,2608385\n"


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.ui = MagicMock()
        self.ui.session_state = {}
        self.ui.file_uploader.return_value = BytesIO(DATA)
        self.ui.selectbox.side_effect = lambda label, options, **kw: options[0]
        self.ui.text_input.return_value = "What percentage reached Q30?"
        self.ui.number_input.return_value = None
        self.ui.button.return_value = True
        self.client = MagicMock()
        modules = {"streamlit": self.ui, "openai": SimpleNamespace(OpenAI=self.client)}
        patcher = patch.dict(sys.modules, modules)
        patcher.start()
        self.addCleanup(patcher.stop)
        from src.genomeflow import review
        patch_ui = patch.object(review, "st", self.ui)
        patch_ui.start()
        self.addCleanup(patch_ui.stop)
        self.show = review.show
        self.provider = self.client.return_value.responses.create
        env = patch.dict(os.environ, OPENAI_API_KEY="test-only", OPENAI_MODEL="simulated")
        env.start()
        self.addCleanup(env.stop)

    def test_route_and_repeat(self):
        self.provider.return_value.output_text = "q30"
        self.show()
        self.show()
        self.assertEqual(self.provider.call_count, 1)
        self.assertIn("62.0276%", self.ui.write.call_args.args[0])

    def test_unsupported(self):
        self.provider.return_value.output_text = "unsupported"
        self.show()
        self.ui.info.assert_called_once()
        self.ui.write.assert_not_called()

    def check_fallback(self):
        self.show()
        self.ui.warning.assert_called_once()
        self.assertIn("42,052 reads", self.ui.write.call_args.args[0])
        self.assertFalse(self.ui.session_state["qc_routes"])

    def test_malformed(self):
        self.provider.return_value.output_text = "invented-tool"
        self.check_fallback()

    def test_timeout(self):
        self.provider.side_effect = TimeoutError()
        self.check_fallback()

    def test_invalid_counts(self):
        self.ui.file_uploader.return_value = BytesIO(DATA.replace(b"2608385", b"9999999"))
        self.show()
        self.ui.error.assert_called_once()
        self.provider.assert_not_called()
        self.ui.write.assert_not_called()

    def test_missing_key(self):
        os.environ.pop("OPENAI_API_KEY")
        self.check_fallback()
        self.provider.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
