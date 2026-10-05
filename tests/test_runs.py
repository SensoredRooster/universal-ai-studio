import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import studio_core.runs as runs_mod
from studio_core.runs import ProductionRun


class ProductionRunTests(unittest.TestCase):
    def test_stage_and_artifact_persist(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(runs_mod, "RUNS_DIR", Path(tmp)):
                run = ProductionRun.create("social-short", run_id="test-run")
                run.start_stage("plan")
                run.save_artifact("plan", {"hello": "world"})
                run.complete_stage("plan")

                reopened = ProductionRun.open("test-run")
                self.assertTrue(reopened.stage_complete("plan"))
                self.assertEqual(reopened.load_artifact("plan")["hello"], "world")
                self.assertTrue(reopened.snapshot()["resumable"])

    def test_mark_complete_is_not_resumable(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(runs_mod, "RUNS_DIR", Path(tmp)):
                run = ProductionRun.create("social-short", run_id="done-run")
                run.mark_complete()
                self.assertFalse(run.snapshot()["resumable"])


if __name__ == "__main__":
    unittest.main()
