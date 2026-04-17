"""CUA environment — virtual desktop for computer-use agents.

Registers `computer`, `bash`, and `editor` tools (MCP_TESTING_MODE=1, default)
or orchestration tools `setup_problem` / `grade_problem` (MCP_TESTING_MODE=0).
"""

import logging
import os

from hud import Environment

from dinit_setup import start_dinit

logger = logging.getLogger(__name__)

MCP_TESTING_MODE = os.environ.get("MCP_TESTING_MODE") in ["1", "true"]

# Create the environment
env = Environment("cua-template")


# Agent-visible tools (MCP_TESTING_MODE=1)
if MCP_TESTING_MODE:
    from hud.tools.coding import BashTool, EditTool
    from hud.tools.computer import AnthropicComputerTool

    DISPLAY_WIDTH = int(os.environ.get("DISPLAY_WIDTH", os.environ.get("COMPUTER_WIDTH_PX", "1280")))
    DISPLAY_HEIGHT = int(os.environ.get("DISPLAY_HEIGHT", os.environ.get("COMPUTER_HEIGHT_PX", "800")))

    computer_tool = AnthropicComputerTool(
        display_num=int(os.environ.get("DISPLAY_NUM", "1")),
        width=DISPLAY_WIDTH,
        height=DISPLAY_HEIGHT,
    )
    bash_tool = BashTool()
    edit_tool = EditTool()

    env.add_tool(computer_tool.mcp)
    env.add_tool(bash_tool.mcp)
    env.add_tool(edit_tool.mcp)


# Platform orchestration tools (MCP_TESTING_MODE=0)
if not MCP_TESTING_MODE:

    @env.tool(output_schema=None)
    async def setup_problem(problem_id: str, task_prompt: str | None = None) -> str:
        """Setup the environment for the given task id."""
        logger.info("setup_problem called: %s", problem_id)

        if problem_id not in env._scenarios:
            return f"Unknown problem_id: {problem_id}. Known: {list(env._scenarios.keys())}"

        prompt = await env.run_scenario_setup(problem_id, {})
        if prompt is None:
            return f"Scenario '{problem_id}' setup returned no prompt"

        return task_prompt or prompt

    @env.tool(output_schema=None)
    async def grade_problem(problem_id: str, transcript: str = "") -> dict:
        """Grade the problem by running the scenario's evaluate phase."""
        logger.info("grade_problem called: %s", problem_id)

        await env.submit(problem_id, transcript)
        result = await env.run_scenario_evaluate(problem_id)

        if result is None:
            return {
                "subscores": {"task_pass": 0.0},
                "weights": {"task_pass": 1},
                "metadata": {"error": "evaluation failed"},
            }

        subscores = {}
        weights = {}
        if result.subscores:
            for ss in result.subscores:
                subscores[ss.name] = ss.value
                weights[ss.name] = ss.weight
        else:
            subscores["task_pass"] = result.reward
            weights["task_pass"] = 1

        return {
            "subscores": subscores,
            "weights": weights,
            "metadata": {"score": result.reward, **(result.info or {})},
        }


_dinit_started = False


async def setup_task() -> None:
    """Start the dinit services (virtual desktop stack).

    Safe to call multiple times — only starts once.
    """
    global _dinit_started
    if _dinit_started:
        return
    logger.info("Starting dinit services")
    await start_dinit()
    _dinit_started = True
    logger.info("Dinit services started")


def make_prompt(description: str) -> str:
    """Format a task description into an agent prompt."""
    return f"Use computer use tools to complete the following task:\n\n{description}"


@env.scenario("cua-task")
async def cua_task(
    prompt: str,
    bash_checks: list[dict] | None = None,
    grading_criteria: list[str] | None = None,
):
    """General CUA task scenario.

    Boots the desktop, presents the prompt, then grades using any combination
    of deterministic bash checks and LLM-based rubric criteria. Weights are
    normalized so subscores always sum to 1.0.

    Args:
        prompt: The task instruction shown to the agent.
        bash_checks: Optional list of {"name": str, "command": str, "weight": float}
                     dicts for deterministic shell-based grading.
        grading_criteria: Optional list of rubric strings for LLM judge grading.
    """
    from hud.native.graders import BashGrader, Grade, LLMJudgeGrader
    from hud.tools.types import SubScore

    await setup_task()

    answer = yield make_prompt(prompt)

    # Normalize weights to sum to 1.0
    total = sum(c.get("weight", 1.0) for c in (bash_checks or []))
    if grading_criteria:
        total += 1.0
    total = total or 1.0

    graders = []

    if bash_checks:
        for check in bash_checks:
            graders.append(
                BashGrader.grade(
                    name=check["name"],
                    weight=check.get("weight", 1.0) / total,
                    command=check["command"],
                )
            )

    if grading_criteria:
        criteria = [(c, 1.0) for c in grading_criteria]
        graders.append(
            LLMJudgeGrader.grade(
                name="llm_judge",
                weight=1.0 / total,
                answer=str(answer),
                question=prompt,
                criteria=criteria,
            )
        )

    if not graders:
        graders.append(SubScore(name="desktop_running", value=1.0, weight=1.0))

    yield await Grade.gather(*graders)
