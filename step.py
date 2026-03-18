"""CLA action preprocessing for computer use."""

import asyncio
from typing import Any


def preprocess_cla_action(cla_action: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a CLA action to computer_use parameters.

    Args:
        cla_action: A CLA action dictionary

    Returns:
        Dictionary with computer_use parameters
    """
    action_type = cla_action.get("type")
    if not action_type:
        raise ValueError("Action must have a 'type' field")

    params = {}

    match action_type:
        case "click":
            button = cla_action.get("button", "left")
            if button == "left":
                params["action"] = "left_click"
            elif button == "right":
                params["action"] = "right_click"
            elif button == "middle":
                params["action"] = "middle_click"
            else:
                params["action"] = "left_click"

            point = cla_action.get("point")
            if point:
                x, y = point.get("x"), point.get("y")
                if x is not None and y is not None:
                    params["coordinate"] = (int(x), int(y))

            hold_keys = cla_action.get("hold_keys")
            if hold_keys:
                params["text"] = " ".join(hold_keys)

        case "press":
            params["action"] = "key"
            keys = cla_action.get("keys", [])
            if keys:
                params["text"] = " ".join(keys)

        case "keyup" | "keydown":
            params["action"] = "hold_key"
            keys = cla_action.get("keys", [])
            if keys:
                params["text"] = " ".join(keys)
                params["duration"] = 0.01

        case "type":
            params["action"] = "type"
            params["text"] = cla_action.get("text", "")

        case "scroll":
            params["action"] = "scroll"

            point = cla_action.get("point")
            if point:
                x, y = point.get("x"), point.get("y")
                if x is not None and y is not None:
                    params["coordinate"] = (int(x), int(y))

            scroll = cla_action.get("scroll", {})
            scroll_x = scroll.get("x", 0)
            scroll_y = scroll.get("y", 0)

            if scroll_y > 0:
                params["scroll_direction"] = "down"
                params["scroll_amount"] = abs(int(scroll_y))
            elif scroll_y < 0:
                params["scroll_direction"] = "up"
                params["scroll_amount"] = abs(int(scroll_y))
            elif scroll_x > 0:
                params["scroll_direction"] = "right"
                params["scroll_amount"] = abs(int(scroll_x))
            elif scroll_x < 0:
                params["scroll_direction"] = "left"
                params["scroll_amount"] = abs(int(scroll_x))
            else:
                params["scroll_direction"] = "down"
                params["scroll_amount"] = 1

            hold_keys = cla_action.get("hold_keys")
            if hold_keys:
                params["text"] = " ".join(hold_keys)

        case "move":
            params["action"] = "mouse_move"

            point = cla_action.get("point")
            if point:
                x, y = point.get("x"), point.get("y")
                if x is not None and y is not None:
                    params["coordinate"] = (int(x), int(y))

        case "wait":
            params["action"] = "wait"
            time_ms = cla_action.get("time", 1000)
            params["duration"] = float(time_ms) / 1000.0

        case "drag":
            params["action"] = "left_click_drag"

            path = cla_action.get("path", [])
            if len(path) >= 2:
                start_point = path[0]
                end_point = path[-1]
                start_x, start_y = start_point.get("x"), start_point.get("y")
                end_x, end_y = end_point.get("x"), end_point.get("y")
                if all(coord is not None for coord in [start_x, start_y, end_x, end_y]):
                    params["start_coordinate"] = (int(start_x), int(start_y))
                    params["coordinate"] = (int(end_x), int(end_y))

        case "screenshot":
            params["action"] = "screenshot"

        case _:
            raise ValueError(f"Unsupported action type: {action_type}")

    return params


def extract_text_and_screenshot(content_blocks) -> tuple[str, str]:
    """
    Extract text and screenshot data from computer_use content blocks.

    Args:
        content_blocks: List of TextContent and ImageContent objects

    Returns:
        Tuple of (text, screenshot) where both are strings
    """
    text_parts = []
    screenshot = ""

    if isinstance(content_blocks, list):
        for block in content_blocks:
            if hasattr(block, "type") and block.type == "text":
                if hasattr(block, "text"):
                    text_content = str(block.text)
                    text_parts.append(text_content)
            elif hasattr(block, "type") and block.type == "image":
                if hasattr(block, "data"):
                    screenshot = str(block.data)

    text = "\n".join(text_parts) if text_parts else ""

    return text, screenshot


def step(actions: list[dict[str, Any]]) -> Any:
    """Execute a sequence of actions."""
    from tools.computer import ComputerTool

    computer_tool = ComputerTool()

    all_text_parts = []
    latest_screenshot = ""

    for action in actions:
        try:
            computer_use_params = preprocess_cla_action(action)

            result = asyncio.run(computer_tool(**computer_use_params))

            text, screenshot = extract_text_and_screenshot(result)

            if text:
                all_text_parts.append(text)
            if screenshot:
                latest_screenshot = screenshot

        except Exception as e:
            error_text = f"Error executing action {action.get('type', 'unknown')}: {str(e)}"
            all_text_parts.append(error_text)

    combined_text = "\n".join(all_text_parts) if all_text_parts else ""

    result = {
        "observation": {
            "text": combined_text,
            "screenshot": latest_screenshot,
        }
    }

    return result
