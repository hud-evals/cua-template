"""Task definitions for the cua-template environment.

Each `Task` object below gets picked up by `hud sync tasks`.
Add new tasks by calling `cua_task.task(...)`, setting a `slug`, and
optionally a `validation` list for golden-replay smoke-testing.
"""

from hud.types import MCPToolCall

from env import cua_task


# Navigate to Wikipedia and find the tagline — bash + LLM grading
open_website = cua_task.task(
    prompt=(
        "A Chromium browser is open on the desktop. "
        "Navigate to https://www.wikipedia.org and wait for the page to fully load.\n\n"
        "Once the page is loaded, find the tagline shown below the Wikipedia logo. "
        "Reply with your answer as plain text."
    ),
    bash_checks=[
        {"name": "browser_running", "command": "pgrep -f '/usr/bin/chromium'", "weight": 0.3},
    ],
    grading_criteria=[
        "The agent's answer mentions 'free encyclopedia' in any form — this is part of Wikipedia's tagline",
    ],
)
open_website.slug = "open-website-example"
open_website.validation = [
    MCPToolCall(name="bash", arguments={"command": "sleep 3"}),
    MCPToolCall(
        name="bash",
        arguments={
            "command": (
                "DISPLAY=:1 xdotool key ctrl+l && sleep 0.5 && "
                "DISPLAY=:1 xdotool type 'https://www.wikipedia.org' && "
                "sleep 0.5 && DISPLAY=:1 xdotool key Return && sleep 5"
            )
        },
    ),
]


# Write a text file to the Desktop — deterministic bash grading only
create_document = cua_task.task(
    prompt=(
        "A Chromium browser and an XFCE desktop are available.\n\n"
        "Open a terminal (right-click the desktop and select 'Open Terminal Here', "
        "or find it in Applications > System) and create a file at "
        "/home/ubuntu/Desktop/hello.txt with exactly the content:\n"
        "Hello from HUD!\n\n"
        "You can use any method (echo, nano, cat, etc.)."
    ),
    bash_checks=[
        {"name": "file_exists", "command": "test -f /home/ubuntu/Desktop/hello.txt", "weight": 0.4},
        {"name": "content_correct", "command": "grep -q 'Hello from HUD!' /home/ubuntu/Desktop/hello.txt", "weight": 0.6},
    ],
)
create_document.slug = "create-document-example"
create_document.validation = [
    MCPToolCall(
        name="bash",
        arguments={"command": "echo 'Hello from HUD!' > /home/ubuntu/Desktop/hello.txt"},
    ),
]


# Multi-step research — bash + LLM grading
search_wikipedia = cua_task.task(
    prompt=(
        "A Chromium browser is open on the desktop.\n\n"
        "Navigate to the Wikipedia article about Python (the programming language) at:\n"
        "https://en.wikipedia.org/wiki/Python_(programming_language)\n\n"
        "Find who created Python and in what year it first appeared.\n"
        "Reply with your answer as plain text."
    ),
    bash_checks=[
        {"name": "browser_running", "command": "pgrep -f '/usr/bin/chromium'", "weight": 0.2},
    ],
    grading_criteria=[
        "The agent correctly identifies Guido van Rossum as the creator of Python",
        "The agent mentions that Python first appeared in 1991",
    ],
)
search_wikipedia.slug = "search-wikipedia-python"
search_wikipedia.validation = [
    MCPToolCall(name="bash", arguments={"command": "sleep 3"}),
    MCPToolCall(
        name="bash",
        arguments={
            "command": (
                "DISPLAY=:1 xdotool key ctrl+l && sleep 0.5 && "
                "DISPLAY=:1 xdotool type 'https://en.wikipedia.org/wiki/Python_(programming_language)' && "
                "sleep 0.5 && DISPLAY=:1 xdotool key Return && sleep 5"
            )
        },
    ),
]
