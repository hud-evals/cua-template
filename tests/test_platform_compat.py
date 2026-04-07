"""Tests for HUD platform compatibility.

Verifies:
1. Scenario registration in env._scenarios
2. Tool registration in both MCP_TESTING_MODE and platform mode
3. Full scenario lifecycle: setup -> submit -> evaluate
4. Grade.gather() produces correct EvaluationResult structure
5. grade_problem response matches the expected platform protocol
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, patch


def _fresh_import():
    """Force-reimport env and tasks modules to pick up new env vars."""
    for mod_name in list(sys.modules):
        if mod_name in ("env", "tasks", "tasks.basic", "grading", "grading.graders"):
            del sys.modules[mod_name]

    import env as env_module

    return env_module


# ============================================================================
# Test 1: Scenario is registered
# ============================================================================


def test_scenario_registered():
    """The open-website scenario should be in env._scenarios."""
    from env import env

    assert "open-website" in env._scenarios, (
        f"'open-website' not found in scenarios: {list(env._scenarios.keys())}"
    )
    print("  PASS: open-website registered in env._scenarios")


# ============================================================================
# Test 2: Tool registration — testing mode
# ============================================================================


def test_tools_testing_mode():
    """In MCP_TESTING_MODE=1, agent tools should be registered."""
    os.environ["MCP_TESTING_MODE"] = "1"
    env_module = _fresh_import()
    env = env_module.env

    assert env_module.MCP_TESTING_MODE is True

    tool_names = {t.name for t in asyncio.run(env.list_tools())}
    assert "anthropic_computer" in tool_names, f"'anthropic_computer' not in tools: {tool_names}"
    assert "bash" in tool_names, f"'bash' not in tools: {tool_names}"
    assert "edit" in tool_names, f"'edit' not in tools: {tool_names}"
    assert "setup_problem" not in tool_names, f"'setup_problem' should NOT be in tools: {tool_names}"
    print(f"  PASS: testing mode tools = {sorted(tool_names)}")


# ============================================================================
# Test 3: Tool registration — platform mode
# ============================================================================


def test_tools_platform_mode():
    """With MCP_TESTING_MODE=0, platform orchestration tools should be registered."""
    os.environ["MCP_TESTING_MODE"] = "0"
    env_module = _fresh_import()
    env = env_module.env

    assert env_module.MCP_TESTING_MODE is False

    tool_names = {t.name for t in asyncio.run(env.list_tools())}
    assert "setup_problem" in tool_names, f"'setup_problem' not in tools: {tool_names}"
    assert "grade_problem" in tool_names, f"'grade_problem' not in tools: {tool_names}"
    assert "anthropic_computer" not in tool_names, f"'anthropic_computer' should NOT be in tools: {tool_names}"
    print(f"  PASS: platform mode tools = {sorted(tool_names)}")


# ============================================================================
# Test 4: Full scenario lifecycle (setup -> submit -> evaluate)
# ============================================================================


def test_scenario_lifecycle():
    """Run the scenario generator through its full lifecycle, mocking dinit."""
    os.environ["MCP_TESTING_MODE"] = "1"
    env_module = _fresh_import()
    env = env_module.env

    async def _run():
        with patch("env.start_dinit", new_callable=AsyncMock):
            prompt = await env.run_scenario_setup("open-website", {})

            assert prompt is not None, "Setup returned no prompt"
            assert "wikipedia.org" in prompt, f"Prompt doesn't contain task description: {prompt}"
            print(f"  PASS: setup returned prompt ({len(prompt)} chars)")

            await env.submit("open-website", "I navigated to the page")
            result = await env.run_scenario_evaluate("open-website")

            assert result is not None, "Evaluate returned None"
            assert result.subscores is not None, "Expected subscores, got None"
            assert len(result.subscores) == 2, f"Expected 2 subscores, got {len(result.subscores)}"

            names = {ss.name for ss in result.subscores}
            assert "browser_running" in names, f"Expected 'browser_running' subscore, got {names}"
            assert "page_loaded" in names, f"Expected 'page_loaded' subscore, got {names}"
            print(f"  PASS: evaluate returned reward={result.reward}, subscores={[(s.name, s.value) for s in result.subscores]}")

    asyncio.run(_run())


# ============================================================================
# Test 5: grade_problem response structure (platform protocol)
# ============================================================================


def test_grade_problem_response():
    """Simulate what the platform does: call setup_problem then grade_problem."""
    os.environ["MCP_TESTING_MODE"] = "0"
    env_module = _fresh_import()
    env = env_module.env

    async def _run():
        with patch("env.start_dinit", new_callable=AsyncMock):
            prompt = await env.run_scenario_setup("open-website", {})
            assert prompt is not None

            await env.submit("open-website", "agent transcript here")
            result = await env.run_scenario_evaluate("open-website")

            subscores = {}
            weights = {}
            if result.subscores:
                for ss in result.subscores:
                    subscores[ss.name] = ss.value
                    weights[ss.name] = ss.weight
            else:
                subscores["task_pass"] = result.reward
                weights["task_pass"] = 1

            response = {
                "subscores": subscores,
                "weights": weights,
                "metadata": {"score": result.reward, **(result.info or {})},
            }

            assert "subscores" in response
            assert "weights" in response
            assert "metadata" in response
            assert response["subscores"].keys() == response["weights"].keys()
            assert "browser_running" in response["subscores"]
            assert "page_loaded" in response["subscores"]
            print(f"  PASS: grade_problem response = {response}")

    asyncio.run(_run())


# ============================================================================
# Test 6: BashGrader via Grade.gather()
# ============================================================================


def test_grader_standalone():
    """Test BashGrader produces correct SubScore via Grade.gather()."""
    from grading import BashGrader, Grade

    async def _run():
        result = await Grade.gather(
            BashGrader.grade(weight=1.0, name="true_check", command="true"),
        )

        assert result.reward == 1.0, f"Expected reward=1.0, got {result.reward}"
        assert result.subscores is not None
        assert len(result.subscores) == 1
        assert result.subscores[0].name == "true_check"
        assert result.subscores[0].value == 1.0
        print(f"  PASS: Grade.gather() result = reward={result.reward}, subscores={[(s.name, s.value) for s in result.subscores]}")

    asyncio.run(_run())


# ============================================================================
# Runner
# ============================================================================

if __name__ == "__main__":
    tests = [
        ("Scenario registration", test_scenario_registered),
        ("Tools — testing mode", test_tools_testing_mode),
        ("Tools — platform mode", test_tools_platform_mode),
        ("Scenario lifecycle (setup->submit->evaluate)", test_scenario_lifecycle),
        ("grade_problem response (platform protocol)", test_grade_problem_response),
        ("BashGrader via Grade.gather()", test_grader_standalone),
    ]

    os.environ["MCP_TESTING_MODE"] = "1"

    passed = 0
    failed = 0
    for name, fn in tests:
        print(f"\n[TEST] {name}")
        try:
            fn()
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            failed += 1

    print(f"\n{'=' * 50}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")

    if failed:
        sys.exit(1)
