"""CLI entry points.

These scripts are exposed in pyproject.toml for command-line usage:
- hud_eval: Run the MCP server
- setup_problem: Start dinit + run problem setup, print statement
- grade_problem: Grade a problem, print JSON result
"""

import asyncio
import json
import sys

import click

from env import env, grade_problem_impl, setup_problem_impl


@click.command()
def main() -> None:
    """Run the MCP server."""
    env.run(transport="stdio")


def setup_problem() -> None:
    """Setup a problem: start dinit, run setup, print the statement."""
    if len(sys.argv) != 2:
        print("Usage: setup_problem <problem_id>", file=sys.stderr)
        sys.exit(1)

    problem_id = sys.argv[1]


    statement = asyncio.run(setup_problem_impl(problem_id))
    print(statement)


def grade_problem() -> None:
    """Grade a problem, print JSON with score and subscores."""
    if len(sys.argv) != 2:
        print("Usage: grade_problem <problem_id>", file=sys.stderr)
        sys.exit(1)

    problem_id = sys.argv[1]

    grade = grade_problem_impl(problem_id)
    print(json.dumps({
        "score": float(grade.score),
        "subscores": grade.subscores,
        "weights": grade.weights,
        "metadata": grade.metadata,
    }, indent=2))


if __name__ == "__main__":
    main()
