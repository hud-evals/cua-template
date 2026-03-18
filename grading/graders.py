"""Graders for evaluating agent solutions."""

from .spec import EnvironmentState, SubGrader


class ExampleGrader(SubGrader):
    name = "ExampleGrader"

    @staticmethod
    def compute_score(state: EnvironmentState, **kwargs) -> float:
        # Example grading logic — replace with your own
        return 1.0
