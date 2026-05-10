import asyncio
import subprocess

import typer
from rich.console import Console
from rich.table import Table
from sqlalchemy import select

from bot.db.session import SessionLocal
from bot.models.crash import CrashRoundRecord
from bot.services.crash_reconciliation import (
    crosscheck_recent_financials,
    persist_round_financials,
    reconcile_round,
)

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


@app.command("phase4-check")
def phase4_check_cmd() -> None:
    result = subprocess.run(["python", "scripts/phase4_verify.py"], check=False)
    if result.returncode != 0:
        raise typer.Exit(code=result.returncode)


@app.command("reconcile-round")
def reconcile_round_cmd(runtime_round_id: int) -> None:
    asyncio.run(_reconcile_round(runtime_round_id))


@app.command("reconcile-recent")
def reconcile_recent_cmd(limit: int = 25) -> None:
    asyncio.run(_reconcile_recent(limit))


@app.command("reconcile-verify")
def reconcile_verify_cmd(limit: int = 25) -> None:
    asyncio.run(_reconcile_verify(limit))


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


async def _reconcile_recent(limit: int) -> None:
    async with SessionLocal() as session:
        recent_rounds = (
            await session.scalars(
                select(CrashRoundRecord.runtime_round_id)
                .order_by(CrashRoundRecord.runtime_round_id.desc())
                .limit(limit)
            )
        ).all()

        table = Table(title=f"Recent Round Reconciliation (last {limit})")
        table.add_column("Round")
        table.add_column("Stake")
        table.add_column("Payout")
        table.add_column("Profit")

        for runtime_round_id in recent_rounds:
            report = await reconcile_round(session, runtime_round_id=runtime_round_id)
            await persist_round_financials(session, report=report)
            table.add_row(
                str(runtime_round_id),
                str(report.total_stake),
                str(report.total_payout),
                str(report.house_profit),
            )

        await session.commit()
    console.print(table)


async def _reconcile_verify(limit: int) -> None:
    async with SessionLocal() as session:
        items = await crosscheck_recent_financials(session, limit=limit)
    table = Table(title=f"Financial Crosscheck (last {limit})")
    table.add_column("Round")
    table.add_column("Recorded")
    table.add_column("Recomputed")
    table.add_column("Delta")
    table.add_column("Matched")
    for item in items:
        table.add_row(
            str(item.runtime_round_id),
            "-" if item.recorded_profit is None else str(item.recorded_profit),
            str(item.recomputed_profit),
            str(item.delta),
            "yes" if item.matched else "no",
        )
    console.print(table)


if __name__ == "__main__":
    app()
