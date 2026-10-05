import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import studio_core.runs as runs_mod
from studio_core.runs import ProductionRun
from studio_core.subscript_bridge import build_subscript_job, _validated_local_base


class SubScriptBridgeTests(unittest.TestCase):
    def test_local_url_required(self):
        self.assertEqual(_validated_local_base("http://127.0.0.1:8787"), "http://127.0.0.1:8787")
        with self.assertRaises(ValueError):
            _validated_local_base("https://example.com")

    def test_job_uses_shared_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            video = tmp_path / "clip.mp4"
            video.write_bytes(b"not-real-video")
            with patch.object(runs_mod, "RUNS_DIR", tmp_path / "runs"):
                run = ProductionRun.create("social-short", run_id="bridge-job", request="make a gaming short")
                job = build_subscript_job(run, source_path=str(video), start_seconds=4, duration_seconds=20)
                self.assertEqual(job["contract"], "open-production-job")
                self.assertEqual(job["version"], "1.0")
                self.assertEqual(job["job_id"], "bridge-job")
                self.assertEqual(job["edit"]["duration_seconds"], 20)


if __name__ == "__main__":
    unittest.main()
