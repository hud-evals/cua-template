"""Grading specifications and types for the CUA environment."""

import inspect
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Annotated, Any, Literal

import numpy as np

# ---------------------------------------------------------------------------
# Environment state
# ---------------------------------------------------------------------------


class EnvironmentState:
    """Represents the state of the environment for grading purposes.

    This is a minimal placeholder. Specific problem implementations
    should extend this with domain-specific state attributes.
    """

    def __init__(self, data: str = ""):
        self.data = data


# ---------------------------------------------------------------------------
# Grader name validation
# ---------------------------------------------------------------------------


def validate_grader_name(name: str) -> str:
    """Validate a grader name."""
    if not name:
        raise ValueError("Grader name cannot be empty")
    if not name.isidentifier():
        raise ValueError("Grader name must be a valid Python identifier")
    return name


GraderName = Annotated[str, "A grader name containing only letters, underscores, and hyphens"]


# ---------------------------------------------------------------------------
# SubGrade / Grade
# ---------------------------------------------------------------------------


@dataclass(kw_only=True, frozen=True)
class SubGrade:
    name: GraderName
    score: float
    weight: float
    parameters: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        validate_grader_name(self.name)


@dataclass(kw_only=True)
class Grade:
    """The grade returned by a scenario or the mcp.grade_problem tool."""

    subscores: dict[str, float]
    weights: dict[str, float]
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def score(self):
        assert self.subscores.keys() == self.weights.keys()
        assert np.isclose(sum(self.weights.values()), 1)
        assert min(self.subscores.values()) >= 0
        assert max(self.subscores.values()) <= 1

        score = sum([self.subscores[key] * self.weights[key] for key in self.subscores.keys()])
        return np.clip(score, 0.0, 1.0)

    @staticmethod
    def from_subscores(subscores: list[SubGrade]) -> "Grade":
        # First pass: count occurrences of each name
        name_counts: dict[str, int] = {}
        for subscore in subscores:
            name_counts[subscore.name] = name_counts.get(subscore.name, 0) + 1

        # Second pass: assign final names
        subscores_dict: dict[str, float] = {}
        weights_dict: dict[str, float] = {}
        metadata_dict: dict[str, Any] = {}
        name_usage: dict[str, int] = {}

        for subscore in subscores:
            if isinstance(subscore, Grade):
                continue
            original_name = subscore.name

            if name_counts[original_name] == 1:
                final_name = original_name
            else:
                if original_name not in name_usage:
                    name_usage[original_name] = 1
                else:
                    name_usage[original_name] += 1
                final_name = f"{original_name}-{name_usage[original_name]}"

            subscores_dict[final_name] = subscore.score
            weights_dict[final_name] = subscore.weight

            if subscore.metadata:
                metadata_dict[final_name] = subscore.metadata

        return Grade(
            subscores=subscores_dict,
            weights=weights_dict,
            metadata=metadata_dict,
        )


# ---------------------------------------------------------------------------
# SubGrader base class
# ---------------------------------------------------------------------------


class SubGrader:
    name: str = "BaseGrader"

    @staticmethod
    def compute_score(state: EnvironmentState, **kwargs) -> float:
        raise NotImplementedError("Subclasses must implement this method")

    @classmethod
    def grade(cls, state: EnvironmentState, weight: float, **kwargs) -> SubGrade:
        return SubGrade(
            name=cls.name,
            weight=weight,
            score=cls.compute_score(state, **kwargs),
            parameters=kwargs,
        )

    @classmethod
    def any(cls, weight: float, subgrades: list[SubGrade]) -> SubGrade:
        if any(subgrade.score == 1.0 for subgrade in subgrades):
            score = 1.0
        else:
            score = 0.0
        return SubGrade(
            name=f"{cls.name}_any",
            weight=weight,
            score=score,
            parameters={str(idx): subgrade.parameters for idx, subgrade in enumerate(subgrades)},
        )

    @classmethod
    def all(cls, weight: float, subgrades: list[SubGrade]) -> SubGrade:
        if all(subgrade.score == 1.0 for subgrade in subgrades):
            score = 1.0
        else:
            score = 0.0
        return SubGrade(
            name=f"{cls.name}_all",
            weight=weight,
            score=score,
            parameters={str(idx): subgrade.parameters for idx, subgrade in enumerate(subgrades)},
        )


# ---------------------------------------------------------------------------
# Problem specification registry
# ---------------------------------------------------------------------------


ReviewLevel = Literal[
    "no-review",
    "creator-reviewed",
    "hud-approved",
    "customer-approved",
]


@dataclass
class ProblemSpec:
    # required fields (no defaults)
    id: str
    description: str
    difficulty: str
    task_type: str
    solution_fn: Callable[[EnvironmentState], Grade] = field(repr=False)
    template: str
    review_level: ReviewLevel
    # optional fields (with defaults)
    config: dict[str, Any] | None = None
    image: str = "cua-template"
    startup_command: str = "hud dev env:env --stdio"
    setup: Callable[[dict[str, Any]], Any] | None = None
    demo: bool = False
    too_hard: bool = False
    seed: bool = False
    file_path: str = field(default="")
    source_code: str = field(default="")
    expected_pass_rate: float | None = None
    line_number: int | None = None
    neogen_metadata: dict[str, Any] | None = None


# Global list of all registered problems
PROBLEM_REGISTRY: list[ProblemSpec] = []


def problem(
    *,
    id: str,
    description: str,
    difficulty: str,
    task_type: str,
    template: str,
    review_level: ReviewLevel,
    config: dict[str, Any] | None = None,
    image: str = "cua-template",
    startup_command: str = "hud dev env:env --stdio",
    setup: Callable[[dict[str, Any]], Any] | None = None,
    demo: bool = False,
    too_hard: bool = False,
    seed: bool = False,
    expected_pass_rate: float | None = None,
    neogen_metadata: dict[str, Any] | None = None,
):
    """Decorator to register a problem spec alongside its grading function."""

    def decorator(fn: Callable[[EnvironmentState], Grade]):
        file_path = inspect.getfile(fn)
        try:
            _, starting_line = inspect.getsourcelines(fn)
        except (OSError, TypeError):
            starting_line = None
        try:
            project_root = os.getcwd()
            relative_path = os.path.relpath(file_path, project_root)
        except ValueError:
            relative_path = file_path

        try:
            source_code = inspect.getsource(fn)
        except (OSError, TypeError):
            source_code = ""

        spec = ProblemSpec(
            id=id,
            description=description,
            difficulty=difficulty,
            task_type=task_type,
            template=template,
            review_level=review_level,
            config=config,
            image=image,
            startup_command=startup_command,
            setup=setup,
            solution_fn=fn,
            demo=demo,
            too_hard=too_hard,
            seed=seed,
            file_path=relative_path,
            source_code=source_code,
            expected_pass_rate=expected_pass_rate,
            line_number=starting_line,
            neogen_metadata=neogen_metadata,
        )
        PROBLEM_REGISTRY.append(spec)
        return fn

    return decorator
