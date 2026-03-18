#!/usr/bin/env python3
"""
Build, validate, run, push Docker images and generate metadata JSON
for the cua-template CUA environment.

Actions:
  -b/--build:     Build Docker image (docker build -t <image> -f Dockerfile.hud .)
  -v/--validate:  Validate problems (baseline_fail + golden_pass, 0 agent steps)
  -r/--run:       Run an agent against problems
  -p/--push:      Push Docker image to registry
  -j/--json:      Generate problem-metadata.json

-b and -v/-r are mutually exclusive. Extra args after -- are forwarded
to the active action:

  Build with extra docker build args:
    uv run imagectl4.py -b -- --no-cache

  Validate with extra docker run args:
    uv run imagectl4.py -v -- -e MY_VAR=value

-p and -j can be combined with either side.

Parallelism uses asyncio throughout. Validation and run tasks for
different problem IDs execute concurrently via asyncio.gather.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import tomllib
from collections.abc import Iterable
from pathlib import Path

import hud
from hud import Environment
from hud.agents.claude import ClaudeAgent

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PYPROJECT_PATH = Path("pyproject.toml")

SCENARIO_NAME = "solve-task"


# ============================================================================
# Image name resolution
# ============================================================================


def read_image_from_pyproject() -> str | None:
    """Read the image name from ``[tool.hud].image`` in pyproject.toml."""
    if not PYPROJECT_PATH.exists():
        return None

    try:
        with open(PYPROJECT_PATH, "rb") as f:
            data = tomllib.load(f)
        return data.get("tool", {}).get("hud", {}).get("image")
    except Exception as exc:
        logger.debug(f"Failed to read pyproject.toml: {exc}")
        return None


def _looks_like_registry_image(image: str) -> bool:
    """Return True if the image name contains a registry prefix (has a '/')."""
    name = image.split("@")[0].split(":")[0]
    return "/" in name


# ============================================================================
# Problem discovery
# ============================================================================


def discover_problem_ids() -> list[str]:
    """Auto-discover all registered problem IDs by importing env.py."""
    import tasks  # noqa: F401 — ensure all @problem() decorators run
    from grading.spec import PROBLEM_REGISTRY

    ids = [spec.id for spec in PROBLEM_REGISTRY]
    logger.info(f"Auto-discovered {len(ids)} problem(s): {ids}")
    return ids


# ============================================================================
# Subprocess helpers (async)
# ============================================================================


async def run_subprocess(cmd: list[str], prefix: str) -> int:
    """Run a subprocess asynchronously, streaming output. Returns exit code."""
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    assert process.stdout is not None
    async for raw_line in process.stdout:
        line = raw_line.decode(errors="replace")
        sys.stdout.write(f"{prefix} {line}")
    await process.wait()
    return process.returncode or 0


# ============================================================================
# Build / Push
# ============================================================================


async def build_image(image: str, *, extra_args: list[str] | None = None) -> bool:
    """Build a single Docker image via ``docker build -t <image> -f Dockerfile.hud .``."""
    logger.info(f"Building image: {image}")
    cmd = ["docker", "build", "-t", image, "-f", "Dockerfile.hud"]
    cmd.extend(extra_args or [])
    cmd.append(".")
    rc = await run_subprocess(cmd, prefix="[build]")
    if rc != 0:
        logger.error(f"Build FAILED for {image} (exit code {rc})")
        return False
    logger.info(f"Build succeeded for {image}")
    return True


async def push_image(image: str) -> bool:
    """Push a single Docker image via ``docker push <image>``."""
    logger.info(f"Pushing image: {image}")
    cmd = ["docker", "push", image]
    rc = await run_subprocess(cmd, prefix="[push]")
    if rc != 0:
        logger.error(f"Push FAILED for {image} (exit code {rc})")
        return False
    logger.info(f"Push succeeded for {image}")
    return True


# ============================================================================
# Validate
# ============================================================================

VALIDATE_MODES = ("baseline_fail", "golden_pass")


async def validate_problem(
    image: str,
    problem_id: str,
    validate_mode: str,
    *,
    docker_args: list[str] | None = None,
) -> tuple[str, str, float | None]:
    """Validate a single problem + mode by running an eval with 0 agent steps."""
    label = f"{problem_id} ({validate_mode})"
    logger.info(f"Validating: {label}")

    env = Environment("cua")
    env.connect_image(image, docker_args=docker_args)

    try:
        task = env(SCENARIO_NAME, problem_id=problem_id, validate_mode=validate_mode)
        async with hud.eval(task, trace=True, quiet=True) as ctx:
            agent = ClaudeAgent.create(model="claude-sonnet-4-5")
            await agent.run(ctx, max_steps=0)
        reward = ctx.reward
    except Exception as exc:
        logger.error(f"Validation error for {label}: {exc}")
        return (problem_id, validate_mode, None)

    return (problem_id, validate_mode, reward)


async def validate_all(
    image: str,
    problem_ids: list[str],
    *,
    docker_args: list[str] | None = None,
) -> tuple[list[str], list[str]]:
    """Validate all problems with both ``baseline_fail`` and ``golden_pass`` modes."""
    coros = [
        validate_problem(image, pid, mode, docker_args=docker_args)
        for pid in problem_ids
        for mode in VALIDATE_MODES
    ]
    results = await asyncio.gather(*coros, return_exceptions=True)

    passed: list[str] = []
    failed: list[str] = []

    for result in results:
        if isinstance(result, BaseException):
            failed.append(f"Exception: {result}")
            continue

        pid, mode, reward = result
        desc = f"{pid} ({mode})"
        if reward == 1.0:
            logger.info(f"  PASS: {desc} -> reward={reward}")
            passed.append(desc)
        else:
            logger.error(f"  FAIL: {desc} -> reward={reward} (expected 1.0)")
            failed.append(desc)

    return passed, failed


# ============================================================================
# Run
# ============================================================================


async def run_problem(
    image: str,
    problem_id: str,
    max_steps: int,
    *,
    docker_args: list[str] | None = None,
) -> tuple[str, float | None]:
    """Run an agent against a problem."""
    logger.info(f"Running problem: {problem_id} (max_steps={max_steps})")

    env = Environment("cua")
    env.connect_image(image, docker_args=docker_args)

    try:
        task = env(SCENARIO_NAME, problem_id=problem_id)
        async with hud.eval(task, trace=True) as ctx:
            agent = ClaudeAgent.create(model="claude-sonnet-4-5")
            await agent.run(ctx, max_steps=max_steps)
        reward = ctx.reward
    except Exception as exc:
        logger.error(f"Run error for {problem_id}: {exc}")
        return (problem_id, None)

    return (problem_id, reward)


async def run_all(
    image: str,
    problem_ids: list[str],
    max_steps: int,
    *,
    docker_args: list[str] | None = None,
) -> tuple[list[tuple[str, float]], list[tuple[str, float | None]]]:
    """Run all problems concurrently with an agent."""
    coros = [run_problem(image, pid, max_steps, docker_args=docker_args) for pid in problem_ids]
    results = await asyncio.gather(*coros, return_exceptions=True)

    succeeded: list[tuple[str, float]] = []
    failed: list[tuple[str, float | None]] = []

    for result in results:
        if isinstance(result, BaseException):
            failed.append((f"Exception: {result}", None))
            continue

        pid, reward = result
        if reward is not None and reward > 0:
            logger.info(f"  {pid} -> reward={reward}")
            succeeded.append((pid, reward))
        else:
            logger.error(f"  {pid} -> reward={reward}")
            failed.append((pid, reward))

    return succeeded, failed


# ============================================================================
# JSON generation
# ============================================================================


def _write_json_obj(data: dict, path: str) -> None:
    """Write a JSON object to *path* with trailing newline."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def _write_json_list(data: list[dict], path: str) -> None:
    """Write a JSON list to *path* with trailing newline."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def generate_json(
    image: str,
    problem_ids: list[str],
) -> None:
    """Generate ``problems-metadata.json`` and ``remote_tasks.json``."""
    import tasks  # noqa: F401 — ensure all @problem() decorators run
    from grading.spec import PROBLEM_REGISTRY

    # Derive env name from image (strip registry prefix)
    env_name = image.rsplit("/", 1)[-1]

    # Build a lookup from problem id -> ProblemSpec
    registry_by_id = {spec.id: spec for spec in PROBLEM_REGISTRY}

    # -- problems-metadata.json --
    problems = []
    for pid in problem_ids:
        spec = registry_by_id.get(pid)
        if spec is None:
            logger.warning(f"Problem '{pid}' not found in PROBLEM_REGISTRY")
            continue
        problems.append({
            "id": spec.id,
            "image": image,
            "startup_command": spec.startup_command,
            "required_tools": ["computer"],
            "scratchpad": "allowed",
            "metadata": {
                "difficulty": spec.difficulty,
                "task_type": spec.task_type,
                "review_level": spec.review_level,
                "description": spec.description,
                "template": spec.template,
            },
        })
    metadata = {
        "problem_set": {
            "owner": "hud-evals",
            "name": "hud-evals-problems",
            "version": "1.0.0",
            "created_at": "2025-04-10T00:00:00Z",
            "description": "HUD Evals Problems",
            "metadata": {
                "category": "spreadsheet",
                "language": "python",
                "difficulty": "beginner",
            },
            "problems": problems,
        }
    }
    _write_json_obj(metadata, "problems-metadata.json")
    logger.info(f"Generated problems-metadata.json with {len(problems)} problem(s)")

    # -- remote_tasks.json (HUD format, used by hud eval) --
    remote_tasks = [
        {
            "env": {"name": env_name},
            "scenario": SCENARIO_NAME,
            "args": {"problem_id": pid},
        }
        for pid in problem_ids
    ]
    _write_json_list(remote_tasks, "remote_tasks.json")
    logger.info(f"Generated remote_tasks.json with {len(remote_tasks)} task(s)")


# ============================================================================
# Main
# ============================================================================


async def async_main(args: argparse.Namespace) -> int:
    """Execute the requested actions in order: build -> validate -> run -> push -> json."""
    image: str | None = args.image
    if not image:
        image = read_image_from_pyproject()
        if image:
            logger.info(f"Using image from pyproject.toml [tool.hud]: {image}")
        else:
            logger.error(
                "No image specified and could not read [tool.hud].image "
                "from pyproject.toml. Pass an image name or add:\n\n"
                "  [tool.hud]\n"
                '  image = "your-image:tag"\n\n'
                "to pyproject.toml."
            )
            return 1

    extra_args: list[str] = args.docker_args or []
    has_failures = False

    if extra_args:
        logger.info(f"Extra args after '--': {extra_args}")

    problem_ids: list[str] = args.ids or []
    needs_problems = args.validate or args.run or args.json
    if not problem_ids and needs_problems:
        problem_ids = discover_problem_ids()
        if not problem_ids:
            logger.error("No problems found. Register problems via @problem() in tasks/.")
            return 1

    # --- Build ---
    if args.build:
        ok = await build_image(image, extra_args=extra_args or None)
        if not ok:
            return 1

    # --- Validate ---
    if args.validate:
        logger.info(
            f"Validating {len(problem_ids)} problem(s) "
            f"x {len(VALIDATE_MODES)} modes ..."
        )
        passed, failed = await validate_all(
            image, problem_ids, docker_args=extra_args or None,
        )

        logger.info("")
        logger.info("Validation summary:")
        if passed:
            logger.info(f"  Passed ({len(passed)}): {', '.join(passed)}")
        if failed:
            logger.error(f"  Failed ({len(failed)}): {', '.join(failed)}")
            has_failures = True

    # --- Run ---
    if args.run:
        logger.info(
            f"Running {len(problem_ids)} problem(s) "
            f"(max_steps={args.max_steps}) ..."
        )
        succeeded, failed_runs = await run_all(
            image, problem_ids, args.max_steps, docker_args=extra_args or None,
        )

        logger.info("")
        logger.info("Run summary:")
        if succeeded:
            logger.info(f"  Succeeded ({len(succeeded)}):")
            for pid, reward in succeeded:
                logger.info(f"    {pid}: reward={reward}")
        if failed_runs:
            logger.error(f"  Failed ({len(failed_runs)}):")
            for pid, reward in failed_runs:
                logger.error(f"    {pid}: reward={reward}")
            has_failures = True

    # --- Push ---
    if args.push:
        if not _looks_like_registry_image(image):
            logger.warning(
                f"Image name '{image}' does not contain a registry prefix "
                f"(e.g. 'myregistry.io/org/image:tag'). "
                f"Pushing a local-only name will likely fail."
            )
        ok = await push_image(image)
        if not ok:
            has_failures = True

    # --- JSON ---
    if args.json:
        generate_json(image, problem_ids)

    return 1 if has_failures else 0


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build, validate, run, push, and generate JSON "
            "for cua-template Docker images."
        ),
    )

    parser.add_argument(
        "image",
        nargs="?",
        default=None,
        help=(
            "Docker image name (e.g. myregistry/cua-template:latest). "
            "If omitted, reads from [tool.hud].image in pyproject.toml."
        ),
    )
    parser.add_argument(
        "--ids",
        nargs="+",
        help="Problem IDs to validate / run (default: all registered problems)",
    )

    # Action flags
    parser.add_argument("-b", "--build", action="store_true", help="Build Docker image")
    parser.add_argument("-p", "--push", action="store_true", help="Push image to registry")
    parser.add_argument("-v", "--validate", action="store_true", help="Validate problems (baseline_fail + golden_pass)")
    parser.add_argument("-r", "--run", action="store_true", help="Run agent against problems")
    parser.add_argument("-j", "--json", action="store_true", help="Generate problem-metadata.json")

    # Options
    parser.add_argument("--max-steps", type=int, default=20, help="Max agent steps for --run (default: 20)")

    raw_argv = list(argv) if argv is not None else sys.argv[1:]
    if "--" in raw_argv:
        split_idx = raw_argv.index("--")
        our_argv = raw_argv[:split_idx]
        docker_args = raw_argv[split_idx + 1:]
    else:
        our_argv = raw_argv
        docker_args = []

    args = parser.parse_args(our_argv)
    args.docker_args = docker_args

    if not any([args.build, args.push, args.validate, args.run, args.json]):
        logger.warning("No action flags provided (-b, -p, -v, -r, -j). Nothing to do.")
        return 0

    if args.build and (args.validate or args.run):
        if docker_args:
            parser.error(
                "-b and -v/-r are mutually exclusive when passing args after --. "
                "Run build and validate/run as separate commands."
            )

    return asyncio.run(async_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
