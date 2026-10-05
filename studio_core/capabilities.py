"""Capability discovery and tool contracts for Universal AI Studio.

This module is intentionally dependency-light.  It gives agents a factual
support envelope before they plan work, while leaving the existing app and
providers untouched.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import os
from pathlib import Path
import shutil
from typing import Any, Callable

import requests


ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class ToolContract:
    name: str
    capability: str
    provider: str
    runtime: str
    stability: str = "beta"
    best_for: tuple[str, ...] = ()
    not_good_for: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    fallback_tools: tuple[str, ...] = ()
    resource_profile: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class CapabilityRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolContract] = {}
        self._probes: dict[str, Callable[[], tuple[str, str]]] = {}

    def register(
        self,
        contract: ToolContract,
        probe: Callable[[], tuple[str, str]] | None = None,
    ) -> None:
        self._tools[contract.name] = contract
        if probe is not None:
            self._probes[contract.name] = probe

    def get(self, name: str) -> ToolContract | None:
        return self._tools.get(name)

    def by_capability(self, capability: str) -> list[ToolContract]:
        return [tool for tool in self._tools.values() if tool.capability == capability]

    def report(self) -> dict[str, Any]:
        tools: list[dict[str, Any]] = []
        capabilities: dict[str, dict[str, Any]] = {}
        for name in sorted(self._tools):
            contract = self._tools[name]
            status, detail = self._status(name, contract)
            entry = asdict(contract)
            entry["status"] = status
            entry["status_detail"] = detail
            tools.append(entry)

            bucket = capabilities.setdefault(
                contract.capability,
                {"available": [], "degraded": [], "unavailable": []},
            )
            bucket.setdefault(status, []).append(name)

        return {
            "tools": tools,
            "capabilities": capabilities,
            "summary": {
                "total": len(tools),
                "available": sum(1 for item in tools if item["status"] == "available"),
                "degraded": sum(1 for item in tools if item["status"] == "degraded"),
                "unavailable": sum(1 for item in tools if item["status"] == "unavailable"),
            },
        }

    def _status(self, name: str, contract: ToolContract) -> tuple[str, str]:
        for dependency in contract.dependencies:
            if dependency.startswith("binary:"):
                binary = dependency.split(":", 1)[1]
                if shutil.which(binary) is None:
                    return "unavailable", f"{binary} is not on PATH"
            elif dependency.startswith("path:"):
                raw = dependency.split(":", 1)[1]
                path = Path(raw)
                if not path.exists():
                    return "unavailable", f"{path} does not exist"
            elif dependency.startswith("env:"):
                key = dependency.split(":", 1)[1]
                if not os.getenv(key):
                    return "unavailable", f"{key} is not configured"

        probe = self._probes.get(name)
        if probe is None:
            return "available", "dependencies satisfied"
        try:
            return probe()
        except Exception as exc:
            return "degraded", f"probe failed: {exc}"


def _probe_ollama() -> tuple[str, str]:
    base = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
    try:
        response = requests.get(f"{base}/api/tags", timeout=0.8)
        response.raise_for_status()
        models = [
            item.get("name", "")
            for item in response.json().get("models", [])
            if item.get("name")
        ]
        planner = os.getenv("PLANNER_MODEL", "qwen2.5-coder:7b-instruct")
        if models and planner not in models:
            return "degraded", f"Ollama reachable; configured planner {planner!r} not found"
        return "available", f"Ollama reachable; {len(models)} model(s) discovered"
    except requests.RequestException:
        return "degraded", "Ollama configured but not reachable right now"


def _probe_comfyui() -> tuple[str, str]:
    base = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/")
    try:
        response = requests.get(f"{base}/system_stats", timeout=0.8)
        response.raise_for_status()
        return "available", "ComfyUI reachable"
    except requests.RequestException:
        comfy_dir = ROOT / "ComfyUI"
        if comfy_dir.exists():
            return "degraded", "ComfyUI is installed but not reachable right now"
        return "unavailable", "ComfyUI is not installed"


def _probe_wan() -> tuple[str, str]:
    models = ROOT / "ComfyUI" / "models"
    diffusion = models / "diffusion_models"
    candidates = (
        diffusion / "wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors",
        diffusion / "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors",
    )
    vae = models / "vae" / "wan_2.1_vae.safetensors"
    text_encoder = models / "text_encoders" / "umt5_xxl_fp8_e4m3fn_scaled.safetensors"
    if any(path.exists() for path in candidates) and vae.exists() and text_encoder.exists():
        return "available", "Wan model set discovered"
    return "unavailable", "Wan model files are incomplete or missing"


def build_default_registry() -> CapabilityRegistry:
    registry = CapabilityRegistry()
    registry.register(
        ToolContract(
            name="ollama_chat",
            capability="llm.chat",
            provider="ollama",
            runtime="local",
            stability="production",
            best_for=("planning", "reasoning", "code assistance"),
            metadata={"configured_model_env": "PLANNER_MODEL"},
        ),
        _probe_ollama,
    )
    registry.register(
        ToolContract(
            name="comfyui_sdxl",
            capability="image.generate",
            provider="comfyui",
            runtime="local_gpu",
            best_for=("local image generation", "social visuals"),
            resource_profile={"gpu_recommended": True},
        ),
        _probe_comfyui,
    )
    registry.register(
        ToolContract(
            name="wan_video",
            capability="video.generate",
            provider="comfyui-wan",
            runtime="local_gpu",
            stability="beta",
            best_for=("local text-to-video", "short motion scenes"),
            not_good_for=("low-VRAM systems",),
            fallback_tools=("comfyui_sdxl",),
            resource_profile={"gpu_required": True, "high_vram": True},
        ),
        _probe_wan,
    )
    registry.register(
        ToolContract(
            name="ffmpeg_compose",
            capability="video.compose",
            provider="ffmpeg",
            runtime="local",
            stability="production",
            dependencies=("binary:ffmpeg",),
            best_for=("composition", "transcoding", "captions", "final delivery"),
        ),
    )
    registry.register(
        ToolContract(
            name="ffprobe_validate",
            capability="video.validate",
            provider="ffmpeg",
            runtime="local",
            stability="production",
            dependencies=("binary:ffprobe",),
            best_for=("output verification", "media metadata", "delivery QA"),
        ),
    )
    return registry
