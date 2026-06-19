# cua-template

A HUD **v6** environment for **computer-use agents**: a virtual Linux desktop (XFCE + Chromium,
managed by [dinit](https://github.com/davmac314/dinit)) published as an **`rfb` (VNC) capability**.
The agent brings its own native computer-use tool and drives the screen; tasks grade the result
server-side with deterministic shell checks and an optional LLM judge.

> **The v6 shape:** the env publishes the raw screen (`rfb`) and declares *zero* tools — the
> *agent* owns the computer tool. That decoupling is the whole point.

## Layout

```
env.py           Environment: rfb capability lifecycle + the cua_task grading template
tasks.py         task definitions (prompt + graders + slug)
dinit.d/         desktop service definitions (Xvfb · x11vnc · websockify · xfce4 · chromium)
dinit_setup.py   dinit startup wrapper
manual_dinit.py  pure-Python dinit (loads dinit.d/, starts the `boot` bundle)
entrypoint.sh    boots the desktop before the control channel serves
Dockerfile.hud   desktop image + v6 control channel (hud serve env:env)
```

## Run

Needs [uv](https://docs.astral.sh/uv/), Python 3.11/3.12, the HUD CLI, and Docker. The virtual
desktop (`Xvfb`/`x11vnc`) is **Linux-only**, so the env runs in a container — not under
`--runtime local` on macOS.

```bash
uv sync
cp .env.example .env          # HUD_API_KEY (LLM judge) + ANTHROPIC_API_KEY (the agent)

docker build -f Dockerfile.hud -t cua-template:dev .
docker run -d --env-file .env -p 8765:8765 cua-template:dev    # serves the env + in-container judge
```

Point a computer-use agent at the served env. The multi-step task wants headroom (`--max-steps 100`);
`hud eval` runs the first task only — add `--full` for all three or `--task-ids <slug>`:

```bash
# Direct to Anthropic — always works, no platform traces
HUD_API_KEY="" ANTHROPIC_API_KEY=sk-ant-... \
  hud eval tasks.py claude --model claude-opus-4-8 --runtime tcp://127.0.0.1:8765 --max-steps 100 -y

# Through the HUD gateway — traces land on hud.ai (HUD_API_KEY from your .env)
hud eval tasks.py claude --model claude-sonnet-4-6 --runtime tcp://127.0.0.1:8765 --max-steps 100 -y
```

**Routing note.** Anthropic's computer-use is a provider-native *beta*, so the gateway path only
works if the HUD gateway forwards the `anthropic-beta` header (recent inference-service). The SDK
prefers the gateway whenever `HUD_API_KEY` is set — so run **through the gateway** for platform
traces, or blank `HUD_API_KEY` to go **direct** (always works, no traces). Either way the container
keeps its own baked `HUD_API_KEY`, so the LLM judge still runs. Any computer-use model works
(`claude-sonnet-4-6` default, `claude-opus-4-8` strongest).

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
| `grading_criteria` | `list[str]` | rubric strings judged by an LLM (needs `HUD_API_KEY`; without it this slot scores 0, never errors) |

Weights are normalized so the reward stays in `[0, 1]` (bash checks share one half, the judge the
other). Underscore-prefix the intermediate Task vars and add each to the `tasks` list — a bare
module-level Task *plus* the list double-counts into a "duplicate slug" error.

> Adding a task needs **no redeploy** — it reuses the baked `cua_task` template, so the new prompt
> and graders travel at eval time. Redeploy only when `env.py`, the `Dockerfile`, or the desktop
> changes.

| Slug | Grading | What it tests |
|------|---------|---------------|
| `open-website-example` | bash + LLM | browser navigation, tagline identification |
| `create-document-example` | bash only | terminal use, deterministic file content |
| `shannon-multistep-research` | bash + LLM | long multi-hop research across pages, then a terminal write |

## Tests

```bash
uv run pytest tests/ -q   # offline: grader composition (no desktop, no keys)
```

The end-to-end check is a real `hud eval` rollout against the running desktop — there's no
golden-replay smoke test (a computer-use agent drives pixels over VNC, not replayable tool calls).
