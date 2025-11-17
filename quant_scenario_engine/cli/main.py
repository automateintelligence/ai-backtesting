"""Typer CLI entrypoint."""

from __future__ import annotations

import typer

from quant_scenario_engine.cli.commands.compare import compare


app = typer.Typer(help="Quant Scenario Engine CLI")


app.command()(compare)


if __name__ == "__main__":
    app()

