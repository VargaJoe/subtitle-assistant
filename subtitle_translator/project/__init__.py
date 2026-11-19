"""Model-independent subtitle projects. No provider or configuration imports."""

from .errors import ProjectError

__all__ = ["ProjectService", "ProjectError"]


def __getattr__(name):
    if name == "ProjectService":
        from .service import ProjectService
        return ProjectService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
