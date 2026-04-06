"""CUA environment - tools for solving computer-use tasks.

This environment provides tools for:
- Computer interaction (mouse, keyboard, screenshots) via xvfb/x11vnc/novnc/xfce4
- File editing with str_replace_editor
- Bash command execution

Tool registration is dual-mode:
- MCP_TESTING_MODE=1 (default in Docker): registers agent-facing tools (computer, editor)
- MCP_TESTING_MODE unset: registers platform orchestration tools (setup_problem, grade_problem)
"""

import html
import logging
import os
from typing import Any, Literal

from hud import Environment

from dinit_setup import start_dinit
from tools import ComputerTool, EditTool, ToolError
from tools.computer import Action, ScrollDirection

logger = logging.getLogger(__name__)

MCP_TESTING_MODE = os.environ.get("MCP_TESTING_MODE") in ["1", "true"]

# Create the environment
env = Environment("cua")

# Tool instances (only used in testing mode)
_computer_tool: ComputerTool | None = None
_edit_tool: EditTool | None = None


@env.initialize
async def initialize() -> None:
    """Initialize the CUA environment tools."""
    global _computer_tool, _edit_tool

    if not MCP_TESTING_MODE:
        logger.info("Platform mode — skipping agent tool initialization")
        return

    logger.info("Initializing CUA environment")
    _computer_tool = ComputerTool()
    _edit_tool = EditTool()
    logger.info("CUA environment initialized")


@env.shutdown
async def shutdown() -> None:
    """Clean up the CUA environment."""
    global _computer_tool, _edit_tool
    _computer_tool = None
    _edit_tool = None
    logger.info("CUA environment shut down")


# ============================================================================
# HTML entity unescaping
# ============================================================================


def _unescape(value: Any) -> Any:
    """Recursively unescape HTML entities in strings.

    Some LLM providers (notably xAI/Grok) return tool-call arguments
    with HTML-encoded characters, which corrupts source code.
    """
    if isinstance(value, str):
        return html.unescape(value)
    if isinstance(value, dict):
        return {k: _unescape(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_unescape(v) for v in value]
    return value


# ============================================================================
# Agent-Visible Tools (MCP_TESTING_MODE=1)
# ============================================================================

if MCP_TESTING_MODE:

    @env.tool()
    async def computer(
        *,
        action: Action,
        text: str | None = None,
        coordinate: tuple[int, int] | None = None,
        start_coordinate: tuple[int, int] | None = None,
        duration: int | float | None = None,
        scroll_direction: ScrollDirection | None = None,
        scroll_amount: int | None = None,
    ) -> list:
        """Interact with the screen, keyboard, and mouse of the current computer.

        Args:
            action: The action to perform (screenshot, key, type, left_click, etc.)
            text: Text to type or key to press
            coordinate: (x, y) coordinate for click/move actions
            start_coordinate: Starting (x, y) for drag actions
            duration: Duration in seconds for hold_key/wait actions
            scroll_direction: Direction to scroll (up, down, left, right)
            scroll_amount: Number of scroll clicks

        Returns:
            List of ImageContent and TextContent blocks
        """
        if _computer_tool is None:
            return []

        return await _computer_tool(
            action=action,
            text=_unescape(text),
            coordinate=coordinate,
            start_coordinate=start_coordinate,
            duration=duration,
            scroll_direction=scroll_direction,
            scroll_amount=scroll_amount,
        )

    @env.tool(
        name="str_replace_editor",
        description="Create and edit files using str_replace_editor. Please use absolute paths for all file names.",
    )
    async def str_replace_editor(
        *,
        command: str,
        path: str,
        file_text: str | None = None,
        view_range: list[int] | None = None,
        old_str: str | None = None,
        new_str: str | None = None,
        insert_line: int | None = None,
    ) -> str:
        """Create and edit files using str_replace_editor.

        Args:
            command: One of 'view', 'create', 'str_replace', 'insert', 'undo_edit'
            path: Absolute path to the file
            file_text: Content for 'create' command
            view_range: [start_line, end_line] for 'view' command
            old_str: String to replace for 'str_replace' command
            new_str: Replacement string for 'str_replace' or 'insert'
            insert_line: Line number for 'insert' command

        Returns:
            The command result or file content
        """
        if _edit_tool is None:
            return "Error: Editor tool not initialized"

        try:
            result = await _edit_tool(
                command=command,
                path=_unescape(path),
                file_text=_unescape(file_text),
                view_range=view_range,
                old_str=_unescape(old_str),
                new_str=_unescape(new_str),
                insert_line=insert_line,
            )
            if result.error:
                return f"Error: {result.error}"
            return result.output or ""
        except ToolError as e:
            return f"Error: {e.message}"


# ============================================================================
# Platform Orchestration Tools (MCP_TESTING_MODE unset)
# ============================================================================

if not MCP_TESTING_MODE:

    @env.tool(output_schema=None)
    async def setup_problem(problem_id: str, **kwargs: Any) -> str:
        """Setup the environment for the given task id."""
        logger.info("setup_problem called: %s", problem_id)

        if problem_id not in env._scenarios:
            return f"Unknown problem_id: {problem_id}. Known: {list(env._scenarios.keys())}"

        prompt = await env.run_scenario_setup(problem_id, {})
        if prompt is None:
            return f"Scenario '{problem_id}' setup returned no prompt"

        return kwargs.get("task_prompt") or prompt

    @env.tool(output_schema=None)
    async def grade_problem(problem_id: str, transcript: str = "", **kwargs: Any) -> dict:
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


# ============================================================================
# Scenario Helpers (called by @env.scenario functions in tasks/)
# ============================================================================

ValidateMode = Literal["baseline_fail", "golden_pass"]


async def setup_task() -> None:
    """Start the dinit services (virtual desktop stack)."""
    logger.info("Starting dinit services")
    await start_dinit()
    logger.info("Dinit services started")


def make_prompt(description: str) -> str:
    """Format a task description into an agent prompt."""
    return f"Use computer use tools to complete the following task:\n\n{description}"


# ============================================================================
# Import and register all scenarios from tasks/
# ============================================================================

import tasks  # noqa: E402, F401 - registers scenarios
