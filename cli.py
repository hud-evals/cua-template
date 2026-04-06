"""CLI entry point for the CUA environment MCP server."""

import click

from env import env


@click.command()
def main() -> None:
    """Run the MCP server."""
    env.run(transport="stdio")


if __name__ == "__main__":
    main()
