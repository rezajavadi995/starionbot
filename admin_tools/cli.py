from __future__ import annotations

import asyncio
import shlex
import subprocess

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table
from sqlalchemy import select

from admin_tools.env_manager import ENV_PATH, load_env_map, mask, set_env_value
from bot.db.session import SessionLocal
from bot.models.crash import CrashRoundRecord
from bot.services.crash_reconciliation import (
    crosscheck_recent_financials,
    persist_round_financials,
    reconcile_round,
)

app = typer.Typer(help="StarionBot terminal management")
console = Console()


MENU_ITEMS = [
    "Configure Redis",
    "Configure PostgreSQL",
    "Connect TON Wallet",
    "Set Telegram Admin IDs",
    "Set Bot Token",
    "Configure Mandatory Join",
    "View Current Configuration",
    "Validate Services",
    "Initialize Database",
    "Webhook Settings",
    "Enable Docker",
    "Reconcile Round",
    "Reconcile Recent",
    "Reconcile Verify",
    "Phase4 Check",
    "Exit",
]


def _run(cmd: str) -> tuple[bool, str]:
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    out = (proc.stdout + "\n" + proc.stderr).strip()
    return proc.returncode == 0, out


def _ensure_service(binary: str, install_cmd: str, service_name: str) -> None:
    ok, _ = _run(f"command -v {shlex.quote(binary)}")
    if not ok:
        console.print(f"[yellow]{binary} not found. Installing...[/yellow]")
        _run(install_cmd)
    _run(f"sudo systemctl enable {service_name}")
    _run(f"sudo systemctl start {service_name}")


def _configure_redis() -> None:
    _ensure_service(
        "redis-server",
        "sudo apt-get update && sudo apt-get install -y redis-server",
        "redis-server",
    )
    username = Prompt.ask("Enter Redis username", default="starion")
    password = Prompt.ask("Enter Redis password", password=True)
    redis_url = f"redis://{username}:{password}@localhost:6379/0"
    set_env_value("REDIS_URL", redis_url)
    console.print("[green]Redis configured and saved to .env[/green]")


def _configure_postgres() -> None:
    _ensure_service(
        "psql",
        "sudo apt-get update && sudo apt-get install -y postgresql postgresql-contrib",
        "postgresql",
    )
    db = Prompt.ask("Enter PostgreSQL database name", default="starionbot")
    user = Prompt.ask("Enter PostgreSQL username", default="starion")
    password = Prompt.ask("Enter PostgreSQL password", password=True)
    create_user_sql = " ".join(
        [
            "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles",
            f"WHERE rolname = '{user}')",
            f"THEN CREATE USER {user} WITH PASSWORD '{password}';",
            "END IF; END $$;",
        ]
    )
    _run(f'sudo -u postgres psql -c "{create_user_sql}"')
    _run(f'sudo -u postgres psql -c "CREATE DATABASE {db} OWNER {user};"')
    _run(f'sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE {db} TO {user};"')
    url = f"postgresql+asyncpg://{user}:{password}@localhost:5432/{db}"
    set_env_value("POSTGRESQL_URL", url)
    _run("alembic upgrade head")
    console.print("[green]PostgreSQL configured and migrations attempted.[/green]")


def _configure_ton() -> None:
    api_key = Prompt.ask("Enter TON API Key", password=True)
    mnemonic = Prompt.ask("Enter TON Wallet Mnemonic", password=True)
    if len(mnemonic.split()) < 12:
        console.print("[red]Mnemonic seems invalid (expected >= 12 words).[/red]")
        return
    set_env_value("TON_API_KEY", api_key)
    set_env_value("TON_WALLET_MNEMONIC", mnemonic)
    console.print("[green]TON credentials saved to .env[/green]")


def _set_admin_ids() -> None:
    admin_ids = Prompt.ask("Enter Telegram Admin IDs (comma-separated)", default="")
    set_env_value("ADMIN_IDS", admin_ids)


def _set_bot_token() -> None:
    token = Prompt.ask("Enter Telegram Bot Token", password=True)
    set_env_value("TELEGRAM_BOT_TOKEN", token)
    validate_cmd = (
        "python - <<'PY'\n"
        "import requests\n"
        f"print(requests.get('https://api.telegram.org/bot{token}/getMe', timeout=10).json())\n"
        "PY"
    )
    ok, out = _run(validate_cmd)
    console.print(
        "[green]Token saved.[/green]" if ok else f"[red]Validation failed:[/red] {out[:200]}"
    )


def _set_mandatory_join() -> None:
    channel = Prompt.ask("Enter mandatory join channel id/username")
    set_env_value("MANDATORY_JOIN_CHANNEL", channel)


def _view_config() -> None:
    data = load_env_map()
    table = Table(title=f"Current Configuration ({ENV_PATH})")
    table.add_column("Key")
    table.add_column("Value")
    for key, value in sorted(data.items()):
        shown = (
            mask(value)
            if any(s in key for s in ["TOKEN", "PASSWORD", "SECRET", "MNEMONIC", "KEY"])
            else value
        )
        table.add_row(key, shown)
    console.print(table)


def _validate_services() -> None:
    checks = {
        "Redis": (
            "python - <<'PY'\n"
            "import redis\n"
            "r=redis.Redis.from_url('redis://localhost:6379/0')\n"
            "print(r.ping())\n"
            "PY"
        ),
        "PostgreSQL": (
            "python - <<'PY'\n"
            "import asyncpg, asyncio\n"
            "async def x():\n"
            " c=await asyncpg.connect('postgresql://localhost/postgres')\n"
            " await c.close(); print('ok')\n"
            "asyncio.run(x())\n"
            "PY"
        ),
        "Migrations": "alembic current",
    }
    for name, cmd in checks.items():
        ok, out = _run(cmd)
        status = "[green]OK[/green]" if ok else "[red]FAIL[/red]"
        console.print(f"{name}: {status}")
        if not ok:
            console.print(out[:300])


def _init_db() -> None:
    ok, out = _run("alembic upgrade head")
    console.print("[green]Database initialized.[/green]" if ok else f"[red]{out}[/red]")


def _webhook_settings() -> None:
    secret = Prompt.ask("Enter WEBHOOK_SECRET", password=True)
    set_env_value("WEBHOOK_SECRET", secret)


def _enable_docker() -> None:
    _run("sudo systemctl enable docker")
    _run("sudo systemctl start docker")
    console.print("[green]Docker service enabled/start attempted.[/green]")


def _menu_loop() -> None:
    while True:
        console.print(Panel("[bold cyan]StarionBot Interactive Setup[/bold cyan]"))
        for idx, item in enumerate(MENU_ITEMS, start=1):
            console.print(f"[{idx}] {item}")
        choice = IntPrompt.ask("Select option", default=1)

        if choice == 1:
            _configure_redis()
        elif choice == 2:
            _configure_postgres()
        elif choice == 3:
            _configure_ton()
        elif choice == 4:
            _set_admin_ids()
        elif choice == 5:
            _set_bot_token()
        elif choice == 6:
            _set_mandatory_join()
        elif choice == 7:
            _view_config()
        elif choice == 8:
            _validate_services()
        elif choice == 9:
            _init_db()
        elif choice == 10:
            _webhook_settings()
        elif choice == 11:
            _enable_docker()
        elif choice == 12:
            runtime_round_id = IntPrompt.ask("Enter runtime round id")
            asyncio.run(_reconcile_round(runtime_round_id))
        elif choice == 13:
            asyncio.run(_reconcile_recent(IntPrompt.ask("Limit", default=25)))
        elif choice == 14:
            asyncio.run(_reconcile_verify(IntPrompt.ask("Limit", default=25)))
        elif choice == 15:
            phase4_check_cmd(strict=Confirm.ask("Run strict checks?", default=False))
        elif choice == 16:
            break

        if not Confirm.ask("Return to main menu?", default=True):
            break


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        _menu_loop()


@app.command("phase4-check")
def phase4_check_cmd(strict: bool = False) -> None:
    command = ["python", "scripts/phase4_verify.py"]
    if strict:
        command.append("--strict")
    result = subprocess.run(command, check=False)
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
