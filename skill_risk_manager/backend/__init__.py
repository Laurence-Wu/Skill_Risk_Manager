"""Platform-neutral scanner backend."""

__all__ = ["ScanService"]


def __getattr__(name: str):
    if name == "ScanService":
        from skill_risk_manager.backend.scan_service import ScanService

        return ScanService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
