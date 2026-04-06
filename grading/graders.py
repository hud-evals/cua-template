"""Graders for evaluating agent solutions."""

from .spec import Grader


class ExampleGrader(Grader):
    name = "ExampleGrader"

    @staticmethod
    def compute_score(**kwargs) -> float:
        # Example grading logic — replace with your own
        return 1.0
