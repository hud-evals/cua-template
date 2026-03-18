import argparse
import json
import logging
import os
import urllib.parse
import webbrowser

# set MCP testing mode to false, so we don't import the tools
os.environ["MCP_TESTING_MODE"] = "0"

import hud_controller.extractors
from hud_controller.spec import PROBLEM_REGISTRY
from hud_controller.utils import import_submodules

logging.basicConfig(level=logging.INFO)

import_submodules(hud_controller.extractors)


def _find_spec(problem_id: str):
    for spec in PROBLEM_REGISTRY:
        if spec.id == problem_id:
            return spec
    return None

# We still need to infer the original URL from the setup lambda, but the config
# is now stored directly on the ProblemSpec.
def _extract_url_from_setup(setup_fn):
    """Inspect constants of the setup function to locate the URL argument."""
    for const in setup_fn.__code__.co_consts:
        if isinstance(const, str) and const.startswith("http"):
            return const
    return None

def build_dev_url(original_url: str, config: dict | None = None) -> str:
    parsed = urllib.parse.urlparse(original_url)
    dev_parsed = parsed._replace(netloc="localhost:5173")
    base_url = urllib.parse.urlunparse(dev_parsed)

    if config:
        config_json = json.dumps(config, separators=(",", ":"))
        encoded_config = urllib.parse.quote_plus(config_json)
        sep = "&" if dev_parsed.query else "?"
        base_url = f"{base_url}{sep}config={encoded_config}"
    return base_url


def main():
    parser = argparse.ArgumentParser(description="Open problem in local dev frontend")
    parser.add_argument("problem_id", help="Problem ID as registered (e.g., 9minecraft-comment-hello-world)")
    args = parser.parse_args()

    spec = _find_spec(args.problem_id)
    if spec is None:
        raise SystemExit(f"Problem '{args.problem_id}' not found in registry")

    if spec.setup is None:
        raise SystemExit("The specified problem does not define a setup function")

    url = _extract_url_from_setup(spec.setup)
    if not url:
        raise SystemExit("Could not determine URL from setup function")

    dev_url = build_dev_url(url, spec.config)
    print(f"Opening {dev_url}")
    webbrowser.open(dev_url)

if __name__ == "__main__":
    main() 