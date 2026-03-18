#!/usr/bin/env python3
import argparse
import json
import logging
import os
import sys
from typing import get_args

# set MCP testing mode to false, so we don't import the tools
os.environ["MCP_TESTING_MODE"] = "0"

import hud_controller.extractors
from hud_controller.spec import PROBLEM_REGISTRY, ReviewLevel
from hud_controller.utils import import_submodules

logging.basicConfig(level=logging.INFO)

import_submodules(hud_controller.extractors)

"""
Generates problems/hud-evals-problems.json from the in-code registry of @problem decorators.
"""

def main():
    parser = argparse.ArgumentParser(description="Generate problems.json, optionally filtering by review_level.")
    
    review_levels = get_args(ReviewLevel)
    for level in review_levels:
        parser.add_argument(
            f"--{level.replace('-', '_')}",  # e.g., --no-review, --creator_reviewed
            action="store_true",
            help=f"Include problems with review level: {level}"
        )
    parser.add_argument(
        "--ids",
        nargs="+",
        help="Include only problems with the specified ids"
    )
    parser.add_argument(
        "--ids-file",
        help="Path to a file containing problem ids, one per line (use '-' for stdin)"
    )
    parser.add_argument(
        "--include-too-hard",
        action="store_true",
        help="Include problems marked as too hard",
        default=False,
    )
    parser.add_argument(
        "--include-demo",
        action="store_true",
        help="Include demo problems",
        default=False,
    )
    parser.add_argument(
        "--template",
        help="Include only problems with the specified template"
    )
    parser.add_argument(
        "--image",
        help="Include only problems with the specified image"
    )

    args = parser.parse_args()

    selected_review_levels = []
    for level in review_levels:
        if getattr(args, level.replace('-', '_')):
            selected_review_levels.append(level)
    selected_ids = set()
    if args.ids:
        selected_ids.update(args.ids)
    if args.ids_file:
        if args.ids_file == "-":
            id_lines = sys.stdin.read().splitlines()
        else:
            with open(args.ids_file) as f:
                id_lines = f.read().splitlines()
        selected_ids.update(line.strip() for line in id_lines if line.strip())

    out = {
        "problem_set": {
            "owner": "hud-evals",
            "name": "hud-evals-problems",
            "version": "1.0.0",
            "created_at": "2025-04-10T00:00:00Z",
            "description": "HUD Evals Problems",
            "metadata": {
                "category": "spreadsheet",
                "language": "python",
                "difficulty": "beginner"
            },
            "problems": []
        }
    }

    filtered_problems = []
    for spec in PROBLEM_REGISTRY:
        if selected_review_levels and spec.review_level not in selected_review_levels:
            continue
        if selected_ids and spec.id not in selected_ids:
            continue
        if spec.too_hard and not args.include_too_hard:
            continue
        if spec.demo and not args.include_demo:
            continue
        if args.template and spec.template != args.template:
            continue
        if args.image:
            spec.image = args.image


        filtered_problems.append(spec)

    for spec in filtered_problems:
        out["problem_set"]["problems"].append({
            "id": spec.id,
            "image": spec.image,
            "startup_command": spec.startup_command,
            "required_tools": [
                "computer"
            ],
            "scratchpad": "allowed",
            "metadata": {
                "difficulty": spec.difficulty,
                "task_type": spec.task_type,
                "review_level": spec.review_level,
                "description": spec.description,
                "template": spec.template,
            }
        })

    logging.info(f"Generated {len(out['problem_set']['problems'])} problems")
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main() 
