"""CUA environment - a virtual Linux desktop served over an `rfb` (VNC) capability.

The desktop (Xvfb :1 + x11vnc on VNC port 5900 + xfce4 + chromium) is booted by
entrypoint.sh at container start; `@env.initialize` waits for the VNC port, then publishes
the `rfb` screen so the harness's computer-use agent can drive it. Tasks grade server-side
in this container via deterministic `BashGrader` checks plus an optional LLM judge.
"""

# NOTE: do NOT add `from __future__ import annotations` here - under it a typed @env.template
# param crashes the sync/deploy manifest path (TypeAdapter on a string forward-ref). Keep
# annotations as real objects. (porting notes 15.E)
import asyncio
import logging
import socket

from hud import Environment
from hud.capabilities import Capability
from hud.graders import BashGrader, LLMJudgeGrader, SubScore, combine
from hud.settings import settings

from dinit_setup import start_dinit

logger = logging.getLogger(__name__)

env = Environment(name="cua-template")  # literal name - `hud deploy` static-parses it (15.J)

_HOST = "127.0.0.1"
_VNC_PORT = 5900  # x11vnc serves the :1 display here (dinit.d/x11vnc pins -rfbport 5900)


# ── rfb (VNC desktop) capability lifecycle ────────────────────────────────────


async def _listening(host: str, port: int, timeout: float = 30.0) -> None:
    """Block until host:port accepts a connection (chromium + xfce boot is heavy)."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        try:
            socket.create_connection((host, port), timeout=0.5).close()
            return
        except OSError:
            await asyncio.sleep(0.2)
    raise RuntimeError(f"VNC server never came up on {host}:{port}")


@env.initialize
async def _up() -> None:
    # entrypoint.sh boots dinit before the control channel serves. If the VNC port is not
    # up yet (e.g. a bare image run without the entrypoint), boot it once here. The env does
    # not accept a client until this hook returns, so waiting for the port closes the race.
    try:
        socket.create_connection((_HOST, _VNC_PORT), timeout=0.5).close()
    except OSError:
        logger.info("VNC not up; starting dinit desktop services")
        await start_dinit()
    await _listening(_HOST, _VNC_PORT)
    # display 0 -> VNC port 5900 + 0. (display is the VNC port offset, NOT the X display :1.)
    env.add_capability(Capability.rfb(name="screen", url=f"rfb://{_HOST}", display=0))


@env.shutdown
async def _down() -> None:
    # The dinit-managed desktop dies with the container; nothing to tear down here.
    logger.info("cua-template shutting down")


# ── task ──────────────────────────────────────────────────────────────────────


def make_prompt(description: str) -> str:
    """Format a task description into an agent prompt."""
    return f"Use computer use tools to complete the following task:\n\n{description}"


@env.template()
async def cua_task(
    prompt: str,
    bash_checks: list[dict] | None = None,
    grading_criteria: list[str] | None = None,
):
    """General CUA task: present the prompt, then grade with any combination of deterministic
    bash checks (run server-side in this container) and an LLM rubric judge.

    `combine` normalizes the positive weights to sum to 1.0, so weights are relative.

    Args:
        prompt: The task instruction shown to the agent.
        bash_checks: Optional list of {"name", "command", "weight"} for shell-based grading.
        grading_criteria: Optional rubric strings for the LLM judge (needs HUD_API_KEY).
    """
    answer = yield make_prompt(prompt)

    # Pre-normalize weights to sum to 1.0 (bash checks + one slot for the judge) so combine's
    # own normalization is a no-op and the displayed subscore weights read as fractions.
    total = sum(c.get("weight", 1.0) for c in (bash_checks or []))
    total += 1.0 if grading_criteria else 0.0
    total = total or 1.0

    graders: list = []

    for check in bash_checks or []:
        graders.append(
            BashGrader.grade(
                weight=check.get("weight", 1.0) / total,
                name=check["name"],
                command=check["command"],
            )
        )

    if grading_criteria:
        judge_weight = 1.0 / total
        if settings.api_key:
            graders.append(
                LLMJudgeGrader.grade(
                    weight=judge_weight,
                    name="llm_judge",
                    answer=str(answer),
                    question=prompt,
                    criteria=[(c, 1.0) for c in grading_criteria],
                )
            )
        else:
            # No key (e.g. a keyless deploy): the judge can't run, so it scores 0 at its real
            # weight instead of erroring the trace. Never re-weight the bash checks. (18.D)
            logger.warning("No HUD_API_KEY: LLM judge skipped; it scores 0 at its weight.")
            graders.append(SubScore(name="llm_judge", weight=judge_weight, value=0.0))

    if not graders:
        graders.append(SubScore(name="desktop_running", value=1.0, weight=1.0))

    yield await combine(*graders)
