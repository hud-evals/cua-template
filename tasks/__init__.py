"""Task auto-discovery.

Each subdirectory under tasks/ is a task package with a task.py that
exports a Task object. This module discovers them all at import time.
"""

import importlib
import pkgutil

from hud.eval.task import Task

tasks: dict[str, Task] = {}
task_ids: dict[str, str] = {}

for _info in pkgutil.iter_modules(__path__, __name__ + "."):
    if not _info.ispkg:
        continue
    mod = importlib.import_module(_info.name)
    pkg_name = _info.name.rsplit(".", 1)[-1]
    for _attr_name, attr in vars(mod).items():
        if isinstance(attr, Task):
            tasks[pkg_name] = attr
            task_slug = getattr(attr, "slug", None)
            if isinstance(task_slug, str) and task_slug:
                task_ids[pkg_name] = task_slug
