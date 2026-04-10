"""Create a text file on the Desktop — deterministic BashGrader example.

No LLM grading needed. Pure bash checks verify file existence and content.
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
                "A Chromium browser and an XFCE desktop are available.\n\n"
                "Open a terminal (right-click the desktop and select 'Open Terminal Here', "
                "or find it in Applications > System) and create a file at "
                "/home/ubuntu/Desktop/hello.txt with exactly the content:\n"
                "Hello from HUD!\n\n"
                "You can use any method (echo, nano, cat, etc.)."
            ),
            "bash_checks": [
                {"name": "file_exists", "command": "test -f /home/ubuntu/Desktop/hello.txt", "weight": 0.4},
                {"name": "content_correct", "command": "grep -q 'Hello from HUD!' /home/ubuntu/Desktop/hello.txt", "weight": 0.6},
            ],
            # No grading_criteria → no LLM judge, purely deterministic
        },
    )
    task.slug = "create-document-example"

    task.validation = [
        MCPToolCall(name="bash", arguments={
            "command": "echo 'Hello from HUD!' > /home/ubuntu/Desktop/hello.txt"
        }),
    ]
