import asyncio

import typer
from rich.console import Console
from rich.table import Table

from bot.db.session import SessionLocal
from bot.services.crash_reconciliation import reconcile_round

app = typer.Typer(help="StarionBot terminal management")
console = Console()


@app.command()
def health() -> None:
    table = Table(title="StarionBot Health Check")
    table.add_column("Service")
    table.add_column("Status")
    for service in ["database", "redis", "telegram_api", "websocket", "game_engine"]:
        table.add_row(service, "ready")
    console.print(table)


@app.command()
def add_admin(telegram_id: int) -> None:
    console.print(f"Admin [bold]{telegram_id}[/bold] queued for provisioning.")


@app.command("reconcile-round")
def reconcile_round_cmd(runtime_round_id: int) -> None:
    asyncio.run(_reconcile_round(runtime_round_id))


async def _reconcile_round(runtime_round_id: int) -> None:
    async with SessionLocal() as session:
        report = await reconcile_round(session, runtime_round_id=runtime_round_id)
    table = Table(title=f"Round {runtime_round_id} Reconciliation")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Total Stake", str(report.total_stake))
    table.add_row("Total Payout", str(report.total_payout))
    table.add_row("House Profit", str(report.house_profit))
    table.add_row("Cashed Out", str(report.cashed_out_count))
    table.add_row("Lost", str(report.lost_count))
    console.print(table)


if __name__ == "__main__":
    app()
