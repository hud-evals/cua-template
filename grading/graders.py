"""Custom graders for CUA environment tasks.

Includes a ScreenshotGrader that takes a screenshot of the current desktop
and uses an LLM to evaluate whether the task was completed.
"""

import asyncio
import base64
import logging
import os
from typing import Any

from hud.native.graders import Grader

logger = logging.getLogger(__name__)


class ScreenshotGrader(Grader):
    """Grade by taking a screenshot and asking an LLM if the task is done.

    Uses scrot to capture the display, encodes it as base64, and sends it
    to Claude via the Anthropic API (or HUD inference gateway) for evaluation.
    """

    name = "ScreenshotGrader"

    @classmethod
    async def compute_score(
        cls,
        question: str = "Was the task completed successfully?",
        display: str = ":1",
        **kwargs: Any,
    ) -> tuple[float, dict[str, Any]]:
        # Take screenshot
        screenshot_path = "/tmp/grading_screenshot.png"
        proc = await asyncio.create_subprocess_exec(
            "scrot", "-D", display, screenshot_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.wait()

        if proc.returncode != 0 or not os.path.exists(screenshot_path):
            return 0.0, {"error": "Failed to capture screenshot"}

        with open(screenshot_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode()

        # Call LLM to evaluate the screenshot
        try:
            from anthropic import AsyncAnthropic

            api_key = os.environ.get("HUD_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
            base_url = os.environ.get("HUD_INFERENCE_URL", "https://inference.hud.ai") if os.environ.get("HUD_API_KEY") else None

            client_kwargs: dict[str, Any] = {"api_key": api_key}
            if base_url:
                client_kwargs["base_url"] = base_url

            client = AsyncAnthropic(**client_kwargs)

            response = await client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=256,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": "image/png", "data": image_b64},
                        },
                        {
                            "type": "text",
                            "text": f"{question}\n\nRespond with ONLY 'yes' or 'no'.",
                        },
                    ],
                }],
            )

            answer = response.content[0].text.strip().lower()
            score = 1.0 if answer.startswith("yes") else 0.0
            return score, {"llm_answer": answer, "question": question}

        except Exception as e:
            logger.error("ScreenshotGrader LLM call failed: %s", e)
            return 0.0, {"error": str(e)}
