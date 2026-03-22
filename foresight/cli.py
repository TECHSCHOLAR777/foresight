import typer
from rich.console import Console
from rich.table import Table
from rich import box

from foresight.storage import init_db, get_snapshots
from foresight.collector import collect_loop, collect_snapshot
from foresight.storage import save_snapshot

app = typer.Typer(
    name="foresight",
    help="Predict system resource exhaustion before it happens.",
    add_completion=False,
)

console = Console()


@app.command()
def collect(
    interval: int = typer.Option(5, help="Seconds between each snapshot."),
    rounds: int = typer.Option(10, help="Number of snapshots to collect."),
) -> None:
    """Collect system metrics and save them to the local database."""
    init_db()
    console.print(
        f"[bold green]Starting collection:[/bold green] "
        f"{rounds} snapshots every {interval}s"
    )
    collect_loop(interval_seconds=interval, rounds=rounds)
    console.print("[bold green]Done.[/bold green] All snapshots saved.")


@app.command()
def show(
    limit: int = typer.Option(10, help="Number of recent snapshots to display."),
) -> None:
    """Show the most recent snapshots from the database."""
    init_db()
    snapshots = get_snapshots(limit=limit)

    if not snapshots:
        console.print("[yellow]No snapshots found. Run 'foresight collect' first.[/yellow]")
        raise typer.Exit()

    table = Table(
        title=f"Last {len(snapshots)} Snapshots",
        box=box.ROUNDED,
        show_lines=True,
    )

    table.add_column("Timestamp", style="cyan", no_wrap=True)
    table.add_column("CPU %", justify="right", style="magenta")
    table.add_column("RAM %", justify="right", style="magenta")
    table.add_column("RAM Used (MB)", justify="right")
    table.add_column("Disk %", justify="right", style="magenta")
    table.add_column("Disk Used (GB)", justify="right")

    for snap in reversed(snapshots):
        table.add_row(
            snap["timestamp"],
            str(snap["cpu_percent"]),
            str(snap["ram_percent"]),
            str(snap["ram_used_mb"]),
            str(snap["disk_percent"]),
            str(snap["disk_used_gb"]),
        )

    console.print(table)


@app.command()
def status() -> None:
    """Show a single live snapshot of current resource usage."""
    init_db()
    snap = collect_snapshot()
    save_snapshot(snap)

    console.print("\n[bold]Current System Status[/bold]\n")

    cpu = snap["cpu_percent"]
    ram = snap["ram_percent"]
    disk = snap["disk_percent"]

    cpu_color = _threshold_color(cpu)
    ram_color = _threshold_color(ram)
    disk_color = _threshold_color(disk)

    console.print(f"  CPU   : [{cpu_color}]{cpu}%[/{cpu_color}]")
    console.print(f"  RAM   : [{ram_color}]{ram}%[/{ram_color}]"
                  f"  ({snap['ram_used_mb']} MB / {snap['ram_total_mb']} MB)")
    console.print(f"  Disk  : [{disk_color}]{disk}%[/{disk_color}]"
                  f"  ({snap['disk_used_gb']} GB / {snap['disk_total_gb']} GB)")
    console.print(f"\n  [dim]Snapshot saved at {snap['timestamp']}[/dim]\n")


def _threshold_color(value: float) -> str:
    if value >= 85:
        return "bold red"
    elif value >= 65:
        return "yellow"
    else:
        return "green"


if __name__ == "__main__":
    app()


