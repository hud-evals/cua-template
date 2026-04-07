# CUA Environment Template

A Computer Use Agent (CUA) environment for agent evaluations. Provides computer interaction (mouse, keyboard, screenshots), file editing, bash execution, and a virtual desktop via xvfb/x11vnc/novnc/xfce4.

> **This is a template.** Before building, customize `Dockerfile.hud` and `tasks/` for your project.

## Quick Start

```bash
uv sync
cp .env.example .env  # Then add your API keys

hud build .
hud eval . claude --all -y --max-steps 15
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
# Run with a Claude agent (view desktop at http://localhost:6080/vnc.html)
hud eval . claude --all -y --max-steps 15

# Validate with golden solutions (no LLM needed)
hud eval . integration_test --all -y
```

### Deploy

```bash
hud deploy .
hud sync tasks my-taskset-name
hud eval my-taskset-name claude --all -y --remote
```

## Key Concepts

### Scenarios vs Tasks

A **scenario** defines a reusable workflow pattern — setup, prompt, grade. This template has one scenario (`cua-task`) that handles all CUA evaluations.

A **task** is a concrete instance of a scenario with specific parameters — the prompt, grading criteria, and validation steps. Tasks live in `tasks/<name>/task.py`.

```python
# tasks/my_task/task.py
task = Task(
    env=env,
    scenario="cua-task",
    args={
        "prompt": "Navigate to example.com and find the page title.",
        "bash_checks": [
            {"name": "browser_running", "command": "pgrep -f chromium", "weight": 0.3},
        ],
        "grading_criteria": [
            "The agent correctly reports the page title",
        ],
    },
)
task.slug = "my-task-slug"
```

### The `cua-task` Scenario

The single scenario accepts three grading parameters:

| Parameter | Type | Purpose |
|-----------|------|---------|
| `prompt` | `str` | Task instruction shown to the agent |
| `bash_checks` | `list[dict]` | Deterministic shell command checks (no LLM needed) |
| `grading_criteria` | `list[str]` | Rubric strings evaluated by LLM judge |

Use `bash_checks` alone for fully deterministic grading, `grading_criteria` alone for LLM-only grading, or both together.

### Included Example Tasks

| Task | Grading | What it demonstrates |
|------|---------|---------------------|
| `open-website-example` | Bash + LLM | Browser navigation, LLM evaluates answer |
| `create-document-example` | Bash only | Desktop interaction, deterministic grading |
| `search-wikipedia-python` | Bash + LLM | Multi-step research, factual LLM evaluation |

### Virtual Desktop Stack

The environment runs a full virtual desktop managed by [dinit](https://github.com/davmac314/dinit):

| Service | Purpose |
|---------|---------|
| `xvfb` | Virtual framebuffer X server |
| `x11vnc` | VNC server |
| `websockify` | WebSocket-to-VNC proxy (port 6080 — view at `http://localhost:6080/vnc.html`) |
| `xfce4_session` | XFCE desktop |
| `chromium` | Chromium browser (auto-starts) |

### Tools

Tools are provided by the HUD SDK:

| Tool | SDK Class | Purpose |
|------|-----------|---------|
| `computer` | `AnthropicComputerTool` | Mouse, keyboard, screenshots |
| `bash` | `BashTool` | Persistent shell session |
| `editor` | `EditTool` | File viewing and editing |

### Dual-Mode Operation

| Mode | Tools Registered | Used By |
|------|-----------------|---------|
| `MCP_TESTING_MODE=1` (default) | `computer`, `bash`, `editor` | HUD platform, local dev |
| `MCP_TESTING_MODE=0` | `setup_problem`, `grade_problem` | External orchestrators |

## Structure

```
cua-template/
├── env.py                      # Environment: tools, scenario, dual-mode
├── cli.py                      # MCP server entry point
├── grading/                    # Custom graders (extends hud.native.graders)
├── tasks/
│   ├── open_website/task.py    # Browser navigation + LLM grading
│   ├── create_document/task.py # File creation + bash grading
│   └── search_wikipedia/task.py # Research + LLM grading
├── dinit.d/                    # Desktop service definitions
├── dinit_setup.py              # Dinit startup logic
├── manual_dinit.py             # Python dinit implementation
├── entrypoint.sh               # Container entrypoint
└── Dockerfile.hud              # Container config
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `COMPUTER_WIDTH_PX` | `1280` | Virtual display width |
| `COMPUTER_HEIGHT_PX` | `800` | Virtual display height |
| `DISPLAY_WIDTH` | `1280` | SDK coordinate width (must match above) |
| `DISPLAY_HEIGHT` | `800` | SDK coordinate height (must match above) |
| `MCP_TESTING_MODE` | `1` | `1` = agent tools, `0` = platform tools |

## Further Reading

- **[HUD Documentation](https://docs.hud.ai)**
- **[HUD Python SDK](https://github.com/hud-evals/hud-python)**
