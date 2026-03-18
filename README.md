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
uv run imagectl4.py cua-template -bvr --ids example-problem
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

There is one generic `solve-task` scenario that accepts a `problem_id` argument. You only need to register problems with the `@problem()` decorator:

```python
from grading import problem, Grade, EnvironmentState

@problem(id="my-task", description="...", difficulty="medium", ...)
def my_task_solution(state: EnvironmentState) -> Grade:
    return Grade.from_subscores([MyGrader.grade(state, 1.0)])
```

The `solve-task` scenario (defined in `tasks/basic.py`) handles setup and grading automatically for any registered problem.

### Dinit Service Management

Services are defined in `dinit.d/` and managed by a Python reimplementation (`manual_dinit.py`). See [dinit_guide.md](dinit_guide.md) and [dinit_quick_reference.md](dinit_quick_reference.md) for details.

## Generate Task JSON

```bash
uv run imagectl4.py -j              # all scenarios
uv run imagectl4.py -j --ids my-task # specific scenarios
```

## Structure

```
cua-template/
├── env.py              # Tools + scenario registration
├── tools/              # computer, editor, bash
├── grading/            # Grading logic and spec
├── tasks/              # Problem definitions
├── dinit.d/            # Service definitions (xvfb, x11vnc, etc.)
├── dinit_setup.py      # Dinit startup logic
├── manual_dinit.py     # Python dinit implementation
├── step.py             # CLA action preprocessing
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

- **[Dinit Guide](dinit_guide.md)** - Comprehensive dinit service documentation
- **[Dinit Quick Reference](dinit_quick_reference.md)** - Quick reference for service definitions
- **[Full Documentation](https://docs.hud.ai)** - HUD platform documentation
