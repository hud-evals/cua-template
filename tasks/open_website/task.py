"""Navigate to Wikipedia and find the tagline — LLM grading example."""

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
                "A Chromium browser is open on the desktop. "
                "Navigate to https://www.wikipedia.org and wait for the page to fully load.\n\n"
                "Once the page is loaded, find the tagline shown below the Wikipedia logo. "
                "Reply with your answer as plain text."
            ),
            "bash_checks": [
                {"name": "browser_running", "command": "pgrep -f '/usr/bin/chromium'", "weight": 0.3},
            ],
            "grading_criteria": [
                "The agent's answer mentions 'free encyclopedia' in any form — this is part of Wikipedia's tagline",
            ],
        },
    )
    task.slug = "open-website-example"

    task.validation = [
        MCPToolCall(name="bash", arguments={"command": "sleep 3"}),
        MCPToolCall(name="bash", arguments={
            "command": "DISPLAY=:1 xdotool key ctrl+l && sleep 0.5 && DISPLAY=:1 xdotool type 'https://www.wikipedia.org' && sleep 0.5 && DISPLAY=:1 xdotool key Return && sleep 5"
        }),
    ]
