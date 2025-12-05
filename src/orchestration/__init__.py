"""DeepAgents orchestration layer (Phase 3 pilot)."""

try:
    from src.orchestration.deep_supervisor import DeepSupervisor

    __all__ = ["DeepSupervisor"]
except ImportError:
    # DeepAgents is optional; exporting empty when not installed keeps imports safe.
    __all__: list[str] = []

