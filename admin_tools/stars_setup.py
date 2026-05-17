from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from decimal import Decimal

from rich.console import Console
from rich.prompt import Confirm, IntPrompt

from admin_tools.env_manager import mask, set_env_value
from bot.services.stars import MIN_STARS_TOPUP_XTR, build_stars_invoice

console = Console()


@dataclass(slots=True)
class StarsSetupResult:
    enabled: bool
    min_topup_xtr: int
    provider: str = "Telegram Stars XTR"


def configure_stars_economy_interactive() -> StarsSetupResult:
    enabled = Confirm.ask("Enable Telegram Stars payments?", default=True)
    set_env_value("STARS_ENABLED", "1" if enabled else "0")
    set_env_value("STARS_CURRENCY", "XTR")
    set_env_value("STARS_PROVIDER", "Telegram Stars XTR")

    if not enabled:
        console.print("[yellow]Telegram Stars payments disabled.[/yellow]")
        return StarsSetupResult(enabled=False, min_topup_xtr=int(MIN_STARS_TOPUP_XTR))

    min_topup = _ask_min_topup()
    set_env_value("STARS_MIN_TOPUP_XTR", str(min_topup))
    sample = build_stars_invoice(user_id=0, amount_xtr=Decimal(min_topup))

    console.print("[green]Telegram Stars economy configured for real XTR payments.[/green]")
    console.print("Provider: Telegram Stars XTR")
    console.print(f"Currency: {sample['currency']}")
    console.print(f"Minimum top-up: {min_topup} XTR")
    console.print(f"Sample payload preview: {mask(str(sample['payload']))}")
    console.print("[cyan]Invoices are sent by the Telegram bot after /addstars <amount>.[/cyan]")
    return StarsSetupResult(enabled=True, min_topup_xtr=min_topup)


def validate_stars_bot_token(bot_token: str) -> bool:
    if not bot_token.strip():
        return False
    url = f"https://api.telegram.org/bot{bot_token}/getMe"
    request = urllib.request.Request(url, method="POST")
    with urllib.request.urlopen(request, timeout=15) as response:
        payload = json.loads(response.read().decode())
    return bool(isinstance(payload, dict) and payload.get("ok"))


def build_stars_deep_link(bot_username: str, amount_xtr: int = 1) -> str:
    if amount_xtr < int(MIN_STARS_TOPUP_XTR):
        raise ValueError("Stars deep-link amount must be at least 1 XTR")
    payload = urllib.parse.quote(f"addstars_{amount_xtr}")
    return f"https://t.me/{bot_username}?start={payload}"


def _ask_min_topup() -> int:
    while True:
        min_topup = IntPrompt.ask("Minimum Stars top-up amount (XTR)", default=1)
        if min_topup >= int(MIN_STARS_TOPUP_XTR):
            return min_topup
        console.print("[red]Telegram Stars top-up minimum must be at least 1 XTR.[/red]")
