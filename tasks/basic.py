"""Basic difficulty tasks."""

from env import env, make_prompt, setup_task
from grading import ExampleGrader, Grade, ValidateMode


@env.scenario("example-task")
async def example_task(validate_mode: ValidateMode | None = None):
    """An example task demonstrating the scenario pattern.

    Each scenario is self-contained: it sets up the environment,
    yields a prompt for the agent, then grades the result.
    """
    await setup_task()

    prompt = make_prompt(
        "Open a text editor and create a file called hello.txt "
        "with the content 'Hello, world!' on the desktop."
    )
    _ = yield prompt

    grade = Grade.from_subscores([ExampleGrader.grade(weight=1.0)])
    yield grade.score


# ==============================================================================
# TEMPLATE: Add your tasks below
# ==============================================================================
#
# @env.scenario("my-task")
# async def my_task(validate_mode: ValidateMode | None = None):
#     await setup_task()
#     prompt = make_prompt("Description of what the agent should do.")
#     _ = yield prompt
#     grade = Grade.from_subscores([MyGrader.grade(weight=1.0)])
#     yield grade.score
