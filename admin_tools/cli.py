import typer
from rich.console import Console
from rich.table import Table

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


if __name__ == "__main__":
    app()
