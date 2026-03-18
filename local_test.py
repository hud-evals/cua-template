"""Local test script for the CUA environment.

Usage:
    # Test standalone tools (no scenario)
    uv run local_test.py tools

    # Test a scenario with an agent
    uv run local_test.py scenario

    # Test with hud dev hot-reload
    hud dev env:env --port 8765
    # Then in another terminal:
    uv run local_test.py scenario
"""

import asyncio
import sys

import hud
from hud import Environment
from hud.agents.claude import ClaudeAgent

IMAGE = "cua-template"


async def test_tools():
    """Test standalone tools without running a scenario."""
    print("=== Test: Standalone Tools ===")
    env = Environment("cua")
    env.connect_image(IMAGE)

    async with env:
        tools = env.as_tools()
        print(f"Tools: {[t.name for t in tools]}")

async def test_scenario():
    """Test the solve-task scenario with example-problem."""
    print("=== Test: solve-task (example-problem) ===")
    env = Environment("cua")
    env.connect_image(IMAGE)

    task = env("solve-task", problem_id="example-problem")
    async with hud.eval(task, trace=True) as ctx:
        agent = ClaudeAgent.create(model="claude-sonnet-4-5")
        await agent.run(ctx, max_steps=10)

    print(f"Reward: {ctx.reward}")
    print("Scenario test passed!")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "tools"

    if mode == "tools":
        asyncio.run(test_tools())
    elif mode == "scenario":
        asyncio.run(test_scenario())
    else:
        print(f"Unknown mode: {mode}. Use 'tools' or 'scenario'.")
        sys.exit(1)
