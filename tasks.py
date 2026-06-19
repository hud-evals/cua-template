"""Task definitions for the cua-template environment.

`hud eval tasks.py` and `hud sync tasks` collect the public `tasks` list. Add a task by
calling `cua_task(...)`, setting a `.slug`, and adding it to the list. Verify a CUA env with a
real `hud eval tasks.py claude --runtime hud` rollout - the rfb desktop cannot run on macOS.
"""

from env import cua_task, env  # noqa: F401  (re-export env for `hud eval tasks.py`)


# Navigate to Wikipedia and read the tagline - bash + LLM grading
_open_website = cua_task(
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
        "The agent's answer mentions 'free encyclopedia' in any form - this is part of Wikipedia's tagline",
    ],
)
_open_website.slug = "open-website-example"


# Write a text file to the Desktop - deterministic bash grading only
_create_document = cua_task(
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
_create_document.slug = "create-document-example"


# Multi-step research - bash + LLM grading
_search_wikipedia = cua_task(
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
_search_wikipedia.slug = "search-wikipedia-python"


tasks = [_open_website, _create_document, _search_wikipedia]
