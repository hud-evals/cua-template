"""Task definitions for CUA environment.

Tasks are scenarios registered via @env.scenario when imported.
The @problem decorator also registers them in PROBLEM_REGISTRY for backward compatibility.
"""

# Import task modules to register their scenarios
from . import basic  # noqa: F401

# Add more task modules here as needed:
# from . import medium  # noqa: F401
# from . import hard  # noqa: F401
