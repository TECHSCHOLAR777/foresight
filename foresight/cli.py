import typer
from rich.console import Console
from rich.table import Table
from rich import box
import plotext as plt

from foresight.storage import get_metric_series, VALID_METRICS

from foresight.storage import init_db, get_snapshots
from foresight.collector import collect_loop, collect_snapshot
from foresight.storage import save_snapshot
from foresight.forecaster import forecast_arima
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


@app.command()
def chart(
    metric: str = typer.Option("cpu_percent", help="Metric to chart."),
    limit: int = typer.Option(50, help="Number of recent snapshots to plot."),
) -> None:
    """Render an ASCII line chart of a metric over time in the terminal."""
    init_db()

    if metric not in VALID_METRICS:
        console.print(f"[red]Invalid metric '{metric}'.[/red]")
        console.print(f"Valid options: {', '.join(sorted(VALID_METRICS))}")
        raise typer.Exit()

    timestamps, values = get_metric_series(metric=metric, limit=limit)

    if len(values) < 2:
        console.print("[yellow]Not enough data to chart. "
                      "Run 'foresight collect' first.[/yellow]")
        raise typer.Exit()

    short_labels = [ts[11:16] for ts in timestamps]
    x_values = list(range(len(values)))

    plt.clear_figure()
    plt.plot(x_values, values, label=metric, marker="braille")
    plt.title(f"{metric} — {short_labels[0]} to {short_labels[-1]} "
              f"({len(values)} snapshots)")
    plt.xlabel("Snapshot index")
    plt.ylabel("Percent (%)")
    plt.ylim(0, 100)
    plt.plotsize(80, 20)
    plt.show()


@app.command()
def forecast(
    metric: str = typer.Option("cpu_percent", help="Metric to forecast."),
    steps: int = typer.Option(10, help="How many snapshots ahead to predict."),
) -> None:
    """Forecast future resource usage using ARIMA."""
    init_db()

    if metric not in VALID_METRICS:
        console.print(f"[red]Invalid metric '{metric}'.[/red]")
        raise typer.Exit()

    console.print(f"\n[bold]Running ARIMA forecast for[/bold] "
                  f"[cyan]{metric}[/cyan]...\n")

    result = forecast_arima(metric=metric, steps=steps)

    trend_color = {
        "rising": "red",
        "falling": "green",
        "stable": "yellow"
    }.get(result["trend_summary"], "white")

    console.print(f"  Last observed : {result['last_observed']}%")
    console.print(f"  Steps ahead   : {result['steps_ahead']}")
    console.print(f"  Trend         : "
                  f"[{trend_color}]{result['trend_summary']}[/{trend_color}]")
    console.print(f"\n  Forecast values (next {steps} snapshots):")

    for i, val in enumerate(result["forecast"], start=1):
        bar = "█" * int(val / 5)
        console.print(f"    Step {i:>2} : {val:>6.2f}%  {bar}")

    console.print()

def _threshold_color(value: float) -> str:
    if value >= 85:
        return "bold red"
    elif value >= 65:
        return "yellow"
    else:
        return "green"


if __name__ == "__main__":
    app()



