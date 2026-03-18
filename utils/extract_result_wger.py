#!/usr/bin/env python3
"""
Reads from mcp_server/solutions.py to run a specific grader.

Example:

```
python utils/extract_result_WGER.py container_id problem_id [--truncate] [--verbose]
```
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description="Extract and grade results from a Docker container using WGER-extractor")
    parser.add_argument("container_id", help="Container ID or name")
    parser.add_argument("problem_id", help="ID of the problem to grade")
    parser.add_argument("--truncate", action="store_true", help="Truncate WGER-extractor output to 100 characters")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output including files and debug logs")
    args = parser.parse_args()

    container = args.container_id
    problem_id = args.problem_id

    # Verify that the container exists
    try:
        subprocess.run(["docker", "inspect", container], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print(f"Error: Container '{container}' does not exist", file=sys.stderr)
        sys.exit(1)

    # Kill any running WGER processes in the container
    subprocess.run(["docker", "exec", container, "killall", "WGER"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Run the extractor as ubuntu and capture output
    try:
        subprocess.run([
            "docker", "exec", container,
            "sudo", "mkdir", "-p", "/home/ubuntu/Downloads"
        ])
        result = subprocess.run([
            "docker", "exec", container,
            "uv", "--directory", "/mcp_server", 
            "run", "python", "-c", f"import hud_controller; import asyncio; result = asyncio.run(hud_controller.app.grade_problem({problem_id!r})); print(result)",
        ], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr}", file=sys.stderr)
        sys.exit(1)
        
    print(result.stdout)

if __name__ == "__main__":
    main()
