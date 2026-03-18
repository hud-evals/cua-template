"""CUA environment - tools for solving computer-use tasks.

This environment provides tools for:
- Computer interaction (mouse, keyboard, screenshots) via xvfb/x11vnc/novnc/xfce4
- File editing with str_replace_editor
- Bash command execution
"""
import json
import logging

from hud import Environment

from dinit_setup import start_dinit
from grading.spec import PROBLEM_REGISTRY, EnvironmentState, Grade, ProblemSpec
from tools import ComputerTool, EditTool, ToolError
from tools.computer import Action, ScrollDirection

logger = logging.getLogger(__name__)

# Create the environment
env = Environment("cua")

# Tool instances
_computer_tool: ComputerTool | None = None
_edit_tool: EditTool | None = None


@env.initialize
async def initialize() -> None:
    """Initialize the CUA environment tools."""
    global _computer_tool, _edit_tool

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
# Agent-Visible Tools
# ============================================================================


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
        text=text,
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
            path=path,
            file_text=file_text,
            view_range=view_range,
            old_str=old_str,
            new_str=new_str,
            insert_line=insert_line,
        )
        if result.error:
            return f"Error: {result.error}"
        return result.output or ""
    except ToolError as e:
        return f"Error: {e.message}"


@env.tool()
async def setup_problem(*, problem_id: str) -> str:
    """Set up the environment for a problem: start services and return the problem statement.

    Args:
        problem_id: The ID of the problem to set up.

    Returns:
        The problem statement for the agent to solve.
    """
    return await setup_problem_impl(problem_id)


@env.tool()
async def grade_problem(*, problem_id: str) -> str:
    """Grade the current state of the environment for a problem.

    Args:
        problem_id: The ID of the problem to grade.

    Returns:
        JSON string with score, subscores, weights, and metadata.
    """

    grade = grade_problem_impl(problem_id)
    return json.dumps({
        "score": float(grade.score),
        "subscores": grade.subscores,
        "weights": grade.weights,
        "metadata": grade.metadata,
    })


# ============================================================================
# Scenario Helpers (called by @env.scenario functions in tasks/)
# ============================================================================


template = """
Use computer use tools to complete the following task:

First, login into the app using the following credentials:
Username: admin
Password: adminadmin

<STATEMENT>
"""


def generate_statement_from_spec(spec: ProblemSpec) -> str:
    return spec.description


def _get_spec(problem_id: str) -> ProblemSpec:
    """Look up a problem spec by id."""
    for spec in PROBLEM_REGISTRY:
        if spec.id == problem_id:
            return spec
    raise ValueError(f"No problem found for id: {problem_id}")


async def setup_problem_impl(problem_id: str) -> str:
    """Start the environment and return the problem statement.

    This is the implementation behind the old setup_problem MCP tool.
    Called by @env.scenario generators.
    """
    spec = _get_spec(problem_id)

    logger.info("=== SETUP_PROBLEM for %s ===", problem_id)

    # Start the dinit services
    await start_dinit()
    logger.info("Dinit services started")

    # Run the setup function
    if spec.setup:
        logger.info("Calling setup function with template: %s", spec.template)
        await spec.setup(spec.template)
        logger.info("Setup function completed")
    else:
        logger.warning("No setup function found for %s", problem_id)

    # Create the full statement
    statement = generate_statement_from_spec(spec)
    return template.replace("<STATEMENT>", statement)


def grade_problem_impl(problem_id: str) -> Grade:
    """Grade the problem and return a Grade object.

    This is the implementation behind the old grade_problem MCP tool.
    Called by @env.scenario generators.
    """
    spec = _get_spec(problem_id)
    state = EnvironmentState("")
    return spec.solution_fn(state)


# ============================================================================
# Import and register all scenarios from tasks/
# ============================================================================

import tasks  # noqa: E402, F401 - registers scenarios
