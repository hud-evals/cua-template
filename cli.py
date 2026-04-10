"""CLI entry point for the CUA environment MCP server."""

from env import env


def main() -> None:
    """Run the MCP server."""
    env.run(transport="stdio")


if __name__ == "__main__":
    main()
