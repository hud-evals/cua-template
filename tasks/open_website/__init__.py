try:
    from .task import task  # noqa: F401
except (ImportError, NameError):
    pass  # Inside container — task not needed, scenarios registered by env.py
