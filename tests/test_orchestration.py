import unittest
from unittest.mock import patch

from studio_core.capabilities import CapabilityRegistry, ToolContract
from studio_core.orchestration import (
    architect_system_prompt,
    inspect_plan,
    ranked_pipelines,
    score_pipeline,
)


class OrchestrationTests(unittest.TestCase):
    def _registry(self):
        registry = CapabilityRegistry()
        for name, cap in [
            ("llm", "llm.chat"),
            ("image", "image.generate"),
            ("compose", "video.compose"),
            ("validate", "video.validate"),
        ]:
            registry.register(ToolContract(name, cap, "test", "local"))
        return registry

    def test_pipeline_scoring_rejects_missing_required_capability(self):
        report = self._registry().report()
        result = score_pipeline(
            {
                "id": "demo",
                "required_capabilities": ["llm.chat", "video.generate"],
                "optional_capabilities": [],
            },
            report,
        )
        self.assertFalse(result["executable"])
        self.assertIn("video.generate", result["missing_required"])

    def test_ranked_pipelines_include_image_and_social(self):
        ids = {item["id"] for item in ranked_pipelines(self._registry())}
        self.assertIn("image-generation", ids)
        self.assertIn("social-short", ids)

    def test_architect_prompt_contains_live_envelope(self):
        prompt = architect_system_prompt(self._registry())
        self.assertIn("LIVE TOOL ENVELOPE", prompt)
        self.assertIn("image.generate", prompt)

    def test_inspector_blocks_unknown_pipeline_without_model_call(self):
        result = inspect_plan({"pipeline_id": "does-not-exist"}, self._registry())
        self.assertFalse(result["approved"])
        self.assertFalse(result["ok"])


if __name__ == "__main__":
    unittest.main()
