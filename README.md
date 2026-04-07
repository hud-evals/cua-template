# CUA Environment Template

A Computer Use Agent (CUA) environment for agent evaluations. Provides computer interaction (mouse, keyboard, screenshots), file editing, bash execution, and a virtual desktop via xvfb/x11vnc/novnc/xfce4.

> **This is a template.** Before building, customize `Dockerfile.hud` and `tasks/` for your project.

## Quick Start

```bash
# Install dependencies
uv sync

# Set up API keys
cp .env.example .env  # Then edit with your keys

# Build, test, and deploy
hud build .
hud eval . claude --all -y --max-steps 10
hud deploy .
```

## Prerequisites

Create a `.env` file with your API keys:
```
HUD_API_KEY=your-hud-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
```

Get keys from [hud.ai/project/api-keys](https://hud.ai/project/api-keys) and [console.anthropic.com](https://console.anthropic.com).

## Getting Started

### Build

```bash
hud build .
```

### Run Locally

```bash
# Run with a Claude agent
hud eval . claude --all -y --max-steps 10

# View the desktop via noVNC while it runs
# Open http://localhost:6080/vnc.html in your browser
```

### Deploy

```bash
hud deploy .
hud sync tasks my-taskset-name
hud eval my-taskset-name claude --all -y --remote
```

## Key Concepts

### Virtual Desktop Stack

The environment runs a full virtual desktop managed by [dinit](https://github.com/davmac314/dinit):

| Service | Purpose |
|---------|---------|
| `xvfb` | Virtual framebuffer X server (display `:1`, configurable resolution) |
| `x11vnc` | VNC server for remote desktop access |
| `websockify` | WebSocket-to-VNC proxy on port 6080 (noVNC web access) |
| `xfce4_session` | XFCE desktop environment |
| `chromium` | Chromium browser (auto-starts with desktop) |
| `mk_xauth` | X authority setup (one-time) |

View the desktop at **http://localhost:6080/vnc.html** during local eval runs.

### Tools

Tools are provided by the HUD SDK:

| Tool | SDK Class | Purpose |
|------|-----------|---------|
| `computer` | `AnthropicComputerTool` | Mouse, keyboard, and screenshot interaction |
| `bash` | `BashTool` | Persistent bash shell session |
| `editor` | `EditTool` | View, create, and edit files |

### Scenarios (in `env.py`)

Scenarios define the agent workflow — setup, prompt, and grading:

```python
from hud.native.graders import BashGrader, Grade

@env.scenario("my-task")
async def my_task(url: str = "https://example.com"):
    await setup_task()  # Starts desktop services
    prompt = make_prompt(f"Navigate to {url} in the browser.")
    _ = yield prompt

    yield await Grade.gather(
        BashGrader.grade(weight=1.0, name="check", command="pgrep -f chromium"),
    )
```

### Tasks (in `tasks/<name>/task.py`)

Tasks are concrete instances of scenarios with validation:

```python
from hud import Environment
from hud.eval.task import Task
from hud.types import MCPToolCall

env = Environment("cua-template")
env.connect_image("cua-template:latest")

task = Task(env=env, scenario="open-website", args={"url": "https://www.wikipedia.org"})
task.slug = "my-task-slug"
task.validation = [
    MCPToolCall(name="bash", arguments={"command": "sleep 5"}),
]
```

### Dual-Mode Operation

The environment runs in two modes controlled by `MCP_TESTING_MODE`:

| Mode | Tools Registered | Used By |
|------|-----------------|---------|
| `MCP_TESTING_MODE=1` | `computer`, `bash`, `editor` | HUD platform, local dev |
| `MCP_TESTING_MODE=0` | `setup_problem`, `grade_problem` | External orchestrators |

Both modes share the same scenario definitions.

## Structure

```
cua-template/
├── env.py              # Environment: tools, scenarios, dual-mode registration
├── cli.py              # MCP server entry point
├── grading/            # Custom graders (extends hud.native.graders)
├── tasks/
│   └── open_website/   # Example task
│       ├── __init__.py
│       └── task.py     # Task definition with validation
├── dinit.d/            # Service definitions (xvfb, x11vnc, chromium, etc.)
├── dinit_setup.py      # Dinit startup logic
├── manual_dinit.py     # Python dinit implementation
├── entrypoint.sh       # Container entrypoint (starts desktop before MCP server)
├── local_test.py       # Dev testing
└── Dockerfile.hud      # Container config
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `COMPUTER_WIDTH_PX` | `1280` | Virtual display width |
| `COMPUTER_HEIGHT_PX` | `800` | Virtual display height |
| `DISPLAY_WIDTH` | `1280` | SDK coordinate scaling width (must match `COMPUTER_WIDTH_PX`) |
| `DISPLAY_HEIGHT` | `800` | SDK coordinate scaling height (must match `COMPUTER_HEIGHT_PX`) |
| `DISPLAY_NUM` | `1` | X display number |
| `MCP_TESTING_MODE` | `1` | Tool registration mode (`1` = agent tools, `0` = platform tools) |

## Further Reading

- **[HUD Documentation](https://docs.hud.ai)** - Full platform documentation
- **[HUD Python SDK](https://github.com/hud-evals/hud-python)** - SDK source and examples
