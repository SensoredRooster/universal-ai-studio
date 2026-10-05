import json
import unittest
from unittest.mock import patch

from studio_core.capabilities import CapabilityRegistry, ToolContract, build_default_registry
from studio_core.pipelines import load_pipeline_catalog, load_pipeline_manifest


class CapabilityRegistryTests(unittest.TestCase):
    def test_registry_groups_capabilities(self):
        registry = CapabilityRegistry()
        registry.register(ToolContract("example", "demo.run", "local", "local"))
        report = registry.report()
        self.assertEqual(report["summary"]["total"], 1)
        self.assertIn("example", report["capabilities"]["demo.run"]["available"])

    @patch("studio_core.capabilities.shutil.which", return_value=None)
    def test_missing_binary_is_unavailable(self, _which):
        registry = CapabilityRegistry()
        registry.register(
            ToolContract(
                name="needs_ffmpeg",
                capability="video.compose",
                provider="ffmpeg",
                runtime="local",
                dependencies=("binary:ffmpeg",),
            )
        )
        report = registry.report()
        self.assertEqual(report["tools"][0]["status"], "unavailable")

    def test_default_registry_has_core_media_capabilities(self):
        registry = build_default_registry()
        names = {tool.name for tool in registry._tools.values()}
        self.assertTrue({"ollama_chat", "ffmpeg_compose", "ffprobe_validate"}.issubset(names))

    def test_social_short_manifest_loads(self):
        manifest = load_pipeline_manifest("social-short")
        self.assertEqual(manifest["id"], "social-short")
        self.assertTrue(any(stage["name"] == "review" for stage in manifest["stages"]))
        json.dumps(manifest)

    def test_pipeline_catalog_includes_social_short(self):
        ids = {item["id"] for item in load_pipeline_catalog()}
        self.assertIn("social-short", ids)


if __name__ == "__main__":
    unittest.main()
