import tempfile
import unittest
from pathlib import Path

from studio_core.qa import inspect_video_file


class MediaQATests(unittest.TestCase):
    def test_missing_file_is_rejected(self):
        report = inspect_video_file(Path(tempfile.gettempdir()) / "uas-does-not-exist.mp4")
        self.assertFalse(report["approved"])
        self.assertTrue(any("file_exists" in error for error in report["errors"]))


if __name__ == "__main__":
    unittest.main()
