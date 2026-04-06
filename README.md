# CUA Environment Template

A Computer Use Agent (CUA) environment for agent evaluations. Provides computer interaction (mouse, keyboard, screenshots), file editing, and a virtual desktop via xvfb/x11vnc/novnc/xfce4.

> **This is a template.** Before building, customize `Dockerfile.hud` and `tasks/` for your project.

## Quick Start

```bash
uv sync
uv run imagectl4.py cua-template -bvr  # Build, validate, and run
```

## Getting Started

### Local

**1. Clone and Initialize**

```bash
git clone https://github.com/hud-evals/cua-template
cd cua-template
uv sync
```

**2. Build, Validate, and Run**

```bash
# Build the Docker image
uv run imagectl4.py cua-template -b

# Validate that your task scenarios and grading are correct
uv run imagectl4.py cua-template -v

# Run an agent against scenarios
uv run imagectl4.py cua-template -r

# Or combine all three
uv run imagectl4.py cua-template -bvr
```

Use `--ids` to target specific scenarios:
```bash
uv run imagectl4.py cua-template -bvr --ids example-task
```

Enable hints for scenarios that support them:
```bash
uv run imagectl4.py cua-template -r --hints
```

### Remote

Deploy to [hud.ai](https://hud.ai):

```bash
hud deploy .
```

## Key Concepts

### Virtual Desktop Stack

The environment runs a full virtual desktop using [dinit](https://github.com/davmac314/dinit) for process management:

| Service | Purpose |
|---------|---------|
| `xvfb` | Virtual framebuffer X server (display `:1`, configurable resolution) |
| `x11vnc` | VNC server for remote desktop access |
| `websockify` | WebSocket-to-VNC proxy on port 6080 (noVNC web access) |
| `xfce4_session` | XFCE desktop environment |
| `mk_xauth` | X authority setup (one-time) |

Resolution is configurable via `COMPUTER_WIDTH_PX` and `COMPUTER_HEIGHT_PX` environment variables (default: 1280x800).

### Tools (in `env.py`)

```python
@env.tool()
async def computer(action: str, ...) -> list:
    """Mouse, keyboard, and screenshot interaction."""

@env.tool(name="str_replace_editor")
async def str_replace_editor(command: str, path: str, ...) -> str:
    """View, create, and edit files."""
```

### Tasks (in `tasks/*.py`)

Each task is a self-contained scenario that owns its setup, prompt, and grading:

```python
from env import env, make_prompt, setup_task
from grading import ExampleGrader, Grade, ValidateMode

@env.scenario("my-task")
async def my_task(validate_mode: ValidateMode | None = None):
    await setup_task()
    prompt = make_prompt("Description of what the agent should do.")
    _ = yield prompt
    grade = Grade.from_subscores([MyGrader.grade(weight=1.0)])
    yield grade.score
```

### Dinit Service Management

Services are defined in `dinit.d/` and managed by a Python reimplementation (`manual_dinit.py`).

## Generate Task JSON

```bash
uv run imagectl4.py -j              # all scenarios
uv run imagectl4.py -j --ids my-task # specific scenarios
```

## Structure

```
cua-template/
├── env.py              # Tools + scenario helpers
├── cli.py              # MCP server entry point
├── tools/              # computer, editor, bash
├── grading/            # Grading logic (Grader base class, Grade)
├── tasks/              # Scenario definitions
├── dinit.d/            # Service definitions (xvfb, x11vnc, etc.)
├── dinit_setup.py      # Dinit startup logic
├── manual_dinit.py     # Python dinit implementation
├── imagectl4.py        # Build/validate/run orchestration
├── local_test.py       # Dev testing
└── Dockerfile.hud      # Container config
```

## Build Arguments

| Variable | Default | Description |
|----------|---------|-------------|
| `COMPUTER_WIDTH_PX` | `1280` | Virtual display width |
| `COMPUTER_HEIGHT_PX` | `800` | Virtual display height |
| `DISPLAY_NUM` | `1` | X display number |

## Further Reading

- **[Full Documentation](https://docs.hud.ai)** - HUD platform documentation
