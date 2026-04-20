# cua-template

HUD environment template for computer-use agents. Runs a virtual Linux desktop (XFCE + Chromium) managed by [dinit](https://github.com/davmac314/dinit), and ships with a reusable `cua-task` scenario for evaluating browser and desktop workflows.

## Setup

```bash
uv sync
cp .env.example .env                # fill in HUD_API_KEY (injected into the deployed container for grading)
hud set HUD_API_KEY=your-key-here   # CLI auth, get one at hud.ai/project/api-keys
```

## Deploy & Run

```bash
hud deploy .                              # deploy the environment (once)
hud sync tasks <taskset-name>             # push tasks to a taskset (fast, re-run on every task change)
hud eval <taskset-name> claude --remote --full
```

**Iteration loop:** `hud deploy` is the slow step — run it once. After that, edit `tasks.py` and re-run `hud sync tasks` (takes seconds). Only redeploy when `env.py` or the Dockerfile changes.

See [Deploy & Go Remote](https://docs.hud.ai/building/running-at-scale) for deploy flags, secrets, and auto-deploy options.

## Scenarios and Tasks

`env.py` defines one scenario, `cua-task`: it boots the desktop, runs the prompt against the agent, and grades the result using any combination of `bash_checks` and `grading_criteria`.

A task is that scenario instantiated with specific arguments. Tasks live in `tasks.py` at the repo root — `hud sync tasks` picks up every `Task` object in the module:

```python
# tasks.py
from hud.types import MCPToolCall
from env import cua_task

my_task = cua_task.task(
    prompt="Navigate to example.com and report the page title.",
    bash_checks=[
        {"name": "browser_running", "command": "pgrep -f chromium", "weight": 0.3},
    ],
    grading_criteria=[
        "The agent correctly reports the page title",
    ],
)
my_task.slug = "my-task-slug"

my_task.validation = [
    MCPToolCall(name="bash", arguments={"command": "echo 'golden path here'"}),
]
```

Each task needs a unique kebab-case `slug` — it's how tasks are identified across syncs and filtered via `--task-ids`. `task.validation` is optional: a list of tool calls that make up a golden solution, replayed by the `integration_test` agent to verify the task end-to-end without an LLM.

> Renaming a slug creates a new task on the platform (the old one stays). Pick carefully.

### Grading

Two knobs, used alone or together. Weights are normalized so the reward stays in `[0, 1]`.

| Parameter | Type | Purpose |
|-----------|------|---------|
| `bash_checks` | `list[{name, command, weight}]` | Shell commands, scored by exit code |
| `grading_criteria` | `list[str]` | Rubric strings evaluated by an LLM judge |

See [Native Graders](https://docs.hud.ai/reference/native-graders) for the full reference.

### Included Tasks

| Slug | Grading | What it tests |
|------|---------|--------------|
| `open-website-example` | bash + LLM | Browser navigation, tagline identification |
| `create-document-example` | bash only | File creation, deterministic content check |
| `search-wikipedia-python` | bash + LLM | Multi-step research, factual accuracy |

## Adding a Task

1. Append a new `cua_task.task(...)` block to `tasks.py`, set a `slug`, and optionally a `validation` list.
2. `hud sync tasks <taskset-name>` — no redeploy needed.

## Structure

```
cua-template/
├── env.py                      # Environment, scenario, grading
├── tasks.py                    # Task definitions
├── cli.py                      # MCP server entrypoint
├── dinit.d/                    # Desktop service definitions
├── dinit_setup.py              # dinit startup wrapper
├── manual_dinit.py             # Pure-Python dinit implementation
├── entrypoint.sh               # Container entrypoint
└── Dockerfile.hud              # Container build
```

## Advanced

### Local development

```bash
hud build .   # build the image locally
hud dev       # run it as an MCP server for Cursor / Claude Code
```

See [Tasks & Evaluation](https://docs.hud.ai/building/tasks-and-evaluation) for other local run modes.

### Smoke-testing tasks

Replay every task's golden `validation` on HUD infrastructure — no LLM involved:

```bash
hud eval <taskset-name> integration_test --remote --full
```

All scores of 1.0 = graders and scenario still line up.

## Further Reading

- [HUD Documentation](https://docs.hud.ai)
- [Scaffolding](https://docs.hud.ai/building/scaffolding) — environments, tools, scenarios
- [Tasks & Evaluation](https://docs.hud.ai/building/tasks-and-evaluation) — local iteration
- [Deploy & Go Remote](https://docs.hud.ai/building/running-at-scale) — platform workflows
