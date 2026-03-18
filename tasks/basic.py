"""Basic difficulty tasks."""

from env import env, grade_problem_impl, setup_problem_impl
from grading import EnvironmentState, ExampleGrader, Grade, problem

# ==============================================================================
# Generic scenario: accepts problem_id, delegates to setup/grade helpers
# ==============================================================================


@env.scenario("solve-task", exclude_tools=["setup_problem", "grade_problem"])
async def solve_task(*, problem_id: str):
    """Solve a task identified by problem_id."""
    prompt = await setup_problem_impl(problem_id)
    _ = yield prompt
    grade = grade_problem_impl(problem_id)
    yield grade.score


# ==============================================================================
# Example Problem
# ==============================================================================


@problem(
    id="example-problem",
    description="An example problem to demonstrate the grading system.",
    difficulty="easy",
    task_type="example",
    template="a",
    review_level="no-review",
)
def example_problem_solution(state: EnvironmentState) -> Grade:
    return Grade.from_subscores([ExampleGrader.grade(state, 1.0)])


# ==============================================================================
# TEMPLATE: Add your tasks below
# ==============================================================================
#
# @problem(
#     id="my-task",
#     description="Description of the task.",
#     difficulty="medium",
#     task_type="web-app",
#     template="my-template",
#     review_level="no-review",
# )
# def my_task_solution(state: EnvironmentState) -> Grade:
#     return Grade.from_subscores([MyGrader.grade(state, 1.0)])
