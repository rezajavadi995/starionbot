from __future__ import annotations

import asyncio
import shlex
import subprocess
from decimal import Decimal

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table
from sqlalchemy import select

from admin_tools.env_manager import ENV_PATH, load_env_map, mask, set_env_value
from admin_tools.prod_setup import (
    backup_environment_artifacts,
    configure_domain_and_ssl,
    configure_nginx,
    configure_telegram_webhook,
    ensure_packages,
    generate_systemd_unit,
    restore_environment_artifacts,
    validate_https_infra,
)
from bot.db.session import SessionLocal
from bot.models.crash import CrashRoundRecord
from bot.services.crash_reconciliation import (
    crosscheck_recent_financials,
    persist_round_financials,
    reconcile_round,
)
from bot.services.stars import build_stars_invoice

app = typer.Typer(help="StarionBot terminal management")
console = Console()


MENU_ITEMS = [
    ("Configure Redis", "تنظیم Redis"),
    ("Configure PostgreSQL", "تنظیم PostgreSQL"),
    ("Connect TON Wallet", "اتصال کیف پول TON"),
    ("Set Telegram Admin IDs", "ثبت شناسه ادمین‌های تلگرام"),
    ("Set Bot Token", "تنظیم توکن ربات"),
    ("Configure Mandatory Join", "تنظیم عضویت اجباری"),
    ("View Current Configuration", "نمایش تنظیمات فعلی"),
    ("Validate Services", "اعتبارسنجی سرویس‌ها"),
    ("Initialize Database", "راه‌اندازی دیتابیس"),
    ("Webhook Settings", "تنظیمات Webhook"),
    ("Enable Docker", "فعال‌سازی Docker"),
    ("Configure Telegram Stars Economy", "تنظیم اقتصاد Telegram Stars"),
    ("Reconcile Round", "تسویه یک راند"),
    ("Reconcile Recent", "تسویه راندهای اخیر"),
    ("Reconcile Verify", "بررسی صحت تسویه"),
    ("Phase4 Check", "چک فاز ۴"),
    ("Configure Domain & SSL", "تنظیم دامنه و SSL"),
    ("Configure Nginx Reverse Proxy", "تنظیم Nginx Reverse Proxy"),
    ("Configure Telegram Webhook URL", "تنظیم URL وبهوک تلگرام"),
    ("Configure Telegram Mini App", "تنظیم مینی‌اپ تلگرام"),
    ("Validate HTTPS Infrastructure", "اعتبارسنجی زیرساخت HTTPS"),
    ("Install Systemd Service", "نصب سرویس systemd"),
    ("WebSocket Smoke Check", "تست سریع WebSocket"),
    ("Backup Ops Config", "بکاپ پیکربندی عملیات"),
    ("Restore Ops Config", "بازیابی پیکربندی عملیات"),
    ("Exit", "خروج"),
]


def _run(cmd: str) -> tuple[bool, str]:
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    out = (proc.stdout + "\n" + proc.stderr).strip()
    return proc.returncode == 0, out


def _parse_subdomains(raw: str) -> list[str]:
    values: list[str] = []
    for item in raw.split(","):
        clean = item.strip().lower()
        if clean:
            values.append(clean)
    return values


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


def _configure_stars_economy() -> None:
    enabled = Confirm.ask("Enable Telegram Stars payments?", default=True)
    set_env_value("STARS_ENABLED", "1" if enabled else "0")
    if not enabled:
        console.print("[yellow]Telegram Stars payments disabled.[/yellow]")
        return

    provider = Prompt.ask("Payment provider", default="Telegram Stars XTR")
    amount = IntPrompt.ask("Sample invoice amount (XTR)", default=100)
    sample = build_stars_invoice(
        user_id=0,
        amount_xtr=Decimal(amount),
        description=provider,
    )
    set_env_value("STARS_CURRENCY", "XTR")
    set_env_value("STARS_PROVIDER", provider)
    console.print("[green]Stars economy configured.[/green]")
    console.print(
        f"Sample invoice payload generated: {sample['payload']} (test only; do not reuse)."
    )


def _configure_domain_ssl() -> None:
    primary = Prompt.ask("Enter primary domain (example: ultraspeed.shop)").strip().lower()
    subdomains_raw = Prompt.ask("Enter subdomains separated by comma", default="cdn,api,panel,app")
    subdomains = _parse_subdomains(subdomains_raw)
    configure_domain_and_ssl(primary, subdomains)
    console.print("[green]Domain, DNS checks, and SSL setup completed.[/green]")


def _configure_nginx_proxy() -> None:
    ensure_packages()
    configure_nginx()
    console.print("[green]Nginx reverse proxy configured and reloaded.[/green]")


def _configure_webhook_url() -> None:
    configure_telegram_webhook()
    console.print("[green]Telegram webhook configured and verified.[/green]")


def _configure_mini_app() -> None:
    current = load_env_map().get("MINIAPP_URL", "")
    url = Prompt.ask("Enter Telegram Mini App URL", default=current or "https://example.com/app")
    set_env_value("MINIAPP_URL", url)
    ok, _ = _run(f"curl -fsS {shlex.quote(url)} >/dev/null")
    if ok:
        console.print("[green]Mini App URL saved and reachable.[/green]")
    else:
        console.print("[yellow]Mini App URL saved, reachability check failed.[/yellow]")


def _setup_all_https() -> None:
    _configure_domain_ssl()
    _configure_nginx_proxy()
    _configure_webhook_url()
    _configure_mini_app()
    _validate_https_menu()


def _validate_https_menu() -> None:
    items = validate_https_infra()
    table = Table(title="HTTPS Infrastructure Validation")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Details")
    for item in items:
        table.add_row(item.name, "OK" if item.ok else "FAIL", item.details)
    console.print(table)


def _install_systemd_service() -> None:
    generate_systemd_unit()
    console.print("[green]systemd service installed: starionbot.service[/green]")


def _websocket_smoke_check() -> None:
    cmd = (
        "python - <<'PY'\n"
        "import asyncio, websockets\n"
        "async def run():\n"
        " uri='ws://127.0.0.1:8000/ws/crash'\n"
        " async with websockets.connect(uri, open_timeout=3) as ws:\n"
        "  msg=await asyncio.wait_for(ws.recv(), timeout=3)\n"
        "  print(msg[:200])\n"
        "asyncio.run(run())\n"
        "PY"
    )
    ok, out = _run(cmd)
    if ok:
        console.print("[green]WebSocket smoke check passed.[/green]")
    else:
        console.print(f"[red]WebSocket smoke check failed:[/red] {out[:300]}")


def _preflight_prod() -> None:
    phase4_check_cmd(strict=True)
    _websocket_smoke_check()
    _validate_https_menu()
    _configure_webhook_url()
    console.print("[green]Production preflight sequence completed.[/green]")


def _backup_ops_config() -> None:
    output_dir = Prompt.ask("Backup output directory", default="./ops-backup")
    created = backup_environment_artifacts(output_dir)
    if created:
        console.print("[green]Backup created:[/green]")
        for item in created:
            console.print(f"- {item}")
    else:
        console.print("[yellow]No files were available to back up.[/yellow]")


def _restore_ops_config() -> None:
    backup_dir = Prompt.ask("Backup directory to restore from", default="./ops-backup")
    restored = restore_environment_artifacts(backup_dir)
    if restored:
        console.print("[green]Restored:[/green]")
        for item in restored:
            console.print(f"- {item}")
    else:
        console.print("[yellow]No matching backup files found to restore.[/yellow]")


def _menu_loop() -> None:
    while True:
        console.print(Panel("[bold cyan]StarionBot Interactive Setup[/bold cyan]"))
        for idx, (item_en, item_fa) in enumerate(MENU_ITEMS, start=1):
            console.print(f"[{idx}] {item_en} / {item_fa}")
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
            _configure_stars_economy()
        elif choice == 13:
            runtime_round_id = IntPrompt.ask("Enter runtime round id")
            asyncio.run(_reconcile_round(runtime_round_id))
        elif choice == 14:
            asyncio.run(_reconcile_recent(IntPrompt.ask("Limit", default=25)))
        elif choice == 15:
            asyncio.run(_reconcile_verify(IntPrompt.ask("Limit", default=25)))
        elif choice == 16:
            phase4_check_cmd(strict=Confirm.ask("Run strict checks?", default=False))
        elif choice == 17:
            _configure_domain_ssl()
        elif choice == 18:
            _configure_nginx_proxy()
        elif choice == 19:
            _configure_webhook_url()
        elif choice == 20:
            _configure_mini_app()
        elif choice == 21:
            _validate_https_menu()
        elif choice == 22:
            _install_systemd_service()
        elif choice == 23:
            _websocket_smoke_check()
        elif choice == 24:
            _backup_ops_config()
        elif choice == 25:
            _restore_ops_config()
        elif choice == 26:
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


@app.command("setup-domain-ssl")
def setup_domain_ssl_cmd(primary_domain: str, subdomains: str = "cdn,api,panel,app") -> None:
    values = _parse_subdomains(subdomains)
    configure_domain_and_ssl(primary_domain.strip().lower(), values)


@app.command("setup-nginx")
def setup_nginx_cmd() -> None:
    ensure_packages()
    configure_nginx()


@app.command("setup-webhook")
def setup_webhook_cmd() -> None:
    configure_telegram_webhook()


@app.command("setup-miniapp")
def setup_miniapp_cmd(url: str) -> None:
    set_env_value("MINIAPP_URL", url.strip())
    ok, _ = _run(f"curl -fsS {shlex.quote(url)} >/dev/null")
    if ok:
        console.print("[green]Mini App URL saved and reachable.[/green]")
    else:
        console.print("[yellow]Mini App URL saved, reachability check failed.[/yellow]")


@app.command("setup-https-all")
def setup_https_all_cmd() -> None:
    _setup_all_https()


@app.command("install-systemd")
def install_systemd_cmd() -> None:
    _install_systemd_service()


@app.command("ws-smoke")
def ws_smoke_cmd() -> None:
    _websocket_smoke_check()


@app.command("preflight-prod")
def preflight_prod_cmd() -> None:
    _preflight_prod()


@app.command("backup-ops")
def backup_ops_cmd(output_dir: str = "./ops-backup") -> None:
    created = backup_environment_artifacts(output_dir)
    if not created:
        console.print("[yellow]No files were available to back up.[/yellow]")
        return
    for item in created:
        console.print(item)


@app.command("restore-ops")
def restore_ops_cmd(backup_dir: str = "./ops-backup") -> None:
    restored = restore_environment_artifacts(backup_dir)
    if not restored:
        console.print("[yellow]No matching backup files found to restore.[/yellow]")
        return
    for item in restored:
        console.print(item)


@app.command("validate-https")
def validate_https_cmd() -> None:
    for item in validate_https_infra():
        console.print(f"{item.name}: {'OK' if item.ok else 'FAIL'} - {item.details}")


if __name__ == "__main__":
    app()
