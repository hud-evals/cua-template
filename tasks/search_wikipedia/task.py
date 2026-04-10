"""Search a Wikipedia article and answer a question — multi-step research example.

Combines BashGrader (browser running) with LLMJudgeGrader (factual accuracy).
The agent must navigate, read, and report specific information.
"""

import os

from hud.eval.task import Task
from hud.types import MCPToolCall

if not os.environ.get("_HUD_DEV_CHILD"):
    from hud import Environment

    IMAGE = os.environ.get("HUD_IMAGE", "cua-template:latest")

    env = Environment("cua-template")
    env.connect_image(IMAGE, docker_args=["-p", "6080:6080"])

    task = Task(
        env=env,
        scenario="cua-task",
        args={
            "prompt": (
                "A Chromium browser is open on the desktop.\n\n"
                "Navigate to the Wikipedia article about Python (the programming language) at:\n"
                "https://en.wikipedia.org/wiki/Python_(programming_language)\n\n"
                "Find who created Python and in what year it first appeared.\n"
                "Reply with your answer as plain text."
            ),
            "bash_checks": [
                {"name": "browser_running", "command": "pgrep -f '/usr/bin/chromium'", "weight": 0.2},
            ],
            "grading_criteria": [
                "The agent correctly identifies Guido van Rossum as the creator of Python",
                "The agent mentions that Python first appeared in 1991",
            ],
        },
    )
    task.slug = "search-wikipedia-python"

    task.validation = [
        MCPToolCall(name="bash", arguments={"command": "sleep 3"}),
        MCPToolCall(name="bash", arguments={
            "command": (
                "DISPLAY=:1 xdotool key ctrl+l && sleep 0.5 && "
                "DISPLAY=:1 xdotool type 'https://en.wikipedia.org/wiki/Python_(programming_language)' && "
                "sleep 0.5 && DISPLAY=:1 xdotool key Return && sleep 5"
            )
        }),
    ]
