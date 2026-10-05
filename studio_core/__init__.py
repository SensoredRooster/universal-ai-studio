"""Core orchestration primitives for Universal AI Studio."""

from .capabilities import CapabilityRegistry, ToolContract, build_default_registry
from .pipelines import load_pipeline_catalog, load_pipeline_manifest
from .orchestration import (
    architect_system_prompt,
    create_production_plan,
    inspect_plan,
    inspector_system_prompt,
    ranked_pipelines,
)
from .qa import inspect_video_file
from .runs import ProductionRun, list_runs

__all__ = [
    "CapabilityRegistry",
    "ToolContract",
    "build_default_registry",
    "load_pipeline_catalog",
    "load_pipeline_manifest",
    "architect_system_prompt",
    "create_production_plan",
    "inspect_plan",
    "inspector_system_prompt",
    "ranked_pipelines",
    "inspect_video_file",
    "ProductionRun",
    "list_runs",
]
