# cua-template

A HUD v6 environment for **computer-use agents**: a virtual Linux desktop (XFCE + Chromium,
managed by [dinit](https://github.com/davmac314/dinit)) served as an **`rfb` (VNC) capability**.
The harness's computer-use agent drives the screen; tasks grade the result server-side with
deterministic shell checks and an optional LLM judge.

## Layout

```
env.py           the Environment: the rfb capability lifecycle + the `cua_task` template + grading
tasks.py         the task definitions (prompts + slugs)
dinit.d/         desktop service definitions (Xvfb, x11vnc, websockify, xfce4, chromium)
dinit_setup.py   dinit startup wrapper       manual_dinit.py  pure-Python dinit
entrypoint.sh    boots the desktop before the control channel serves
Dockerfile.hud   the desktop image + the v6 control channel (`hud serve env:env`)
```

## Run

Needs [uv](https://docs.astral.sh/uv/), Python 3.11/3.12, the HUD CLI, and Docker.

```bash
uv sync
cp .env.example .env    # HUD_API_KEY (LLM-judge grading) + ANTHROPIC_API_KEY (the computer-use agent)
```

> The virtual desktop (`Xvfb`/`x11vnc`) is **Linux-only**, so the env doesn't run under
> `--runtime local` on macOS. Run it in a Linux container.

```bash
docker build -f Dockerfile.hud -t cua-template:dev .
docker run -d -e HUD_API_KEY=$HUD_API_KEY -p 8765:8765 cua-template:dev   # serves the env + LLM judge

# Run a computer-use agent against it (see the note below on the direct key):
HUD_API_KEY="" ANTHROPIC_API_KEY=sk-ant-... \
  hud eval tasks.py claude --runtime tcp://127.0.0.1:8765 --max-steps 30 -y
```

**Computer-use needs a direct Anthropic key.** Anthropic's computer-use is a provider-native beta;
the HUD gateway (the default with just `HUD_API_KEY`) doesn't forward it, so the agent must call
Anthropic directly. The SDK prefers the gateway whenever `HUD_API_KEY` is set, so blank it for the
agent (`HUD_API_KEY=""`) and set `ANTHROPIC_API_KEY`. The container keeps its own baked
`HUD_API_KEY` for the LLM judge. Any computer-use model works (`claude-sonnet-4-6` default,
`--model claude-opus-4-8` for the strongest).

## Tasks & grading

`env.py` defines one template, `cua_task`, instantiated per task in `tasks.py`:

```python
from env import cua_task

_my_task = cua_task(
    prompt="Navigate to example.com and report the page title.",
    bash_checks=[{"name": "browser_running", "command": "pgrep -f chromium", "weight": 0.3}],
    grading_criteria=["The agent correctly reports the page title"],
)
_my_task.slug = "my-task-slug"   # unique kebab-case; add it to the `tasks` list
```

| Knob | Type | How it scores |
|------|------|---------------|
| `bash_checks` | `list[{name, command, weight}]` | shell command run in the container (the desktop the agent drove), scored by exit code |
| `grading_criteria` | `list[str]` | rubric strings judged by an LLM (needs `HUD_API_KEY`; without it, this half scores 0) |

Weights are normalized so the reward stays in `[0, 1]`. Underscore-prefix the intermediate Task
vars and add each to the `tasks` list (a bare module-level Task plus the list double-counts → a
"duplicate slug" error).

| Slug | Grading | What it tests |
|------|---------|---------------|
| `open-website-example` | bash + LLM | browser navigation, tagline identification |
| `create-document-example` | bash only | file creation, deterministic content check |
| `search-wikipedia-python` | bash + LLM | multi-step research, factual accuracy |

## Tests

```bash
uv run pytest tests/ -q   # offline: the grader composition (no desktop, no keys)
```

The end-to-end desktop check is a real `hud eval ... --runtime hud` rollout — there's no
golden-replay smoke test (a computer-use agent drives pixels over VNC, not replayable tool calls).
