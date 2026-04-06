"""Basic difficulty tasks."""

from env import ValidateMode, env, make_prompt, setup_task
from grading import ExampleGrader, Grade


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

    yield await Grade.gather(
        ExampleGrader.grade(weight=1.0),
    )


# ==============================================================================
# TEMPLATE: Add your tasks below
# ==============================================================================
#
# from grading import BashGrader, LLMJudgeGrader, SubScore
# from hud.native.graders import exact_match
#
# @env.scenario("my-task")
# async def my_task(validate_mode: ValidateMode | None = None):
#     await setup_task()
#     prompt = make_prompt("Description of what the agent should do.")
#     answer = yield prompt
#
#     # Option 1: Async graders run in parallel
#     yield await Grade.gather(
#         BashGrader.grade(weight=0.5, command="test -f /home/ubuntu/Desktop/output.txt"),
#         LLMJudgeGrader.grade(weight=0.3, answer=answer, criteria=["Correct"]),
#         SubScore(name="format", value=exact_match(answer, "expected"), weight=0.2),
#     )
#
#     # Option 2: Simple sync subscores
#     yield Grade.from_subscores([
#         SubScore(name="check", value=1.0, weight=1.0),
#     ])
