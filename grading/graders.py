"""Custom graders for evaluating agent solutions.

Extend the SDK's async Grader base class. Each grader implements
``compute_score(**kwargs)`` and returns a float between 0.0 and 1.0.
"""

from typing import Any

from hud.native.graders import Grader


class ExampleGrader(Grader):
    """Example grader — always returns 1.0. Replace with your own logic."""

    name = "ExampleGrader"

    @classmethod
    async def compute_score(cls, **kwargs: Any) -> float:
        return 1.0
