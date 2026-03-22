import os
import time
import typer
from rich.console import Console
from rich.table import Table
from rich import box
import plotext as plt

from foresight.storage import init_db, get_snapshots, get_metric_series, VALID_METRICS
from foresight.storage import save_snapshot
from foresight.collector import collect_loop, collect_snapshot
from foresight.forecaster import (
    forecast_arima,
    forecast_holtwinters,
    forecast_ensemble,
    check_threshold,
    steps_to_human_time,
    parse_horizon,
)


# ─── App Setup ────────────────────────────────────────────────────────────────

app = typer.Typer(
    name="foresight",
    help="Predict system resource exhaustion before it happens.",
    add_completion=False,
)

console = Console()

# Smart thresholds based on real computer health standards
METRIC_THRESHOLDS = {
    "cpu_percent":  {"warning": 75.0,  "critical": 90.0},
    "ram_percent":  {"warning": 80.0,  "critical": 90.0},
    "disk_percent": {"warning": 85.0,  "critical": 95.0},
    "ram_used_mb":  {"warning": 80.0,  "critical": 90.0},
    "disk_used_gb": {"warning": 85.0,  "critical": 95.0},
}

VALID_MODELS = ("arima", "holtwinters", "ensemble")


# ─── Private Helpers ──────────────────────────────────────────────────────────

def _color(value: float, warning: float = 75.0, critical: float = 90.0) -> str:
    """Return Rich color string based on value vs thresholds."""
    if value >= critical:
        return "bold red"
    elif value >= warning:
        return "yellow"
    else:
        return "green"


def _run_forecast(metric: str, steps: int, model: str) -> dict:
    """Run the selected forecast model and return result dict."""
    if model == "arima":
        return forecast_arima(metric=metric, steps=steps)
    elif model == "holtwinters":
        return forecast_holtwinters(metric=metric, steps=steps)
    else:
        return forecast_ensemble(metric=metric, steps=steps)


def _validate_inputs(metric: str, model: str) -> bool:
    """Validate metric and model. Print error and return False if invalid."""
    if metric not in VALID_METRICS:
        console.print(f"[red]Invalid metric '{metric}'.[/red]")
        console.print(f"Valid metrics: {', '.join(sorted(VALID_METRICS))}")
        return False
    if model not in VALID_MODELS:
        console.print(
            f"[red]Invalid model '{model}'. "
            f"Choose: {', '.join(VALID_MODELS)}[/red]"
        )
        return False
    return True


def _status_icon(status: str) -> str:
    return {"critical": "🚨", "warning": "⚠️ ", "ok": "✅"}.get(status, "")


def _status_style(status: str) -> str:
    return {
        "critical": "bold red",
        "warning": "bold yellow",
        "ok": "bold green",
    }.get(status, "white")


# ─── Commands ─────────────────────────────────────────────────────────────────

@app.command()
def collect(
    interval: int = typer.Option(
        60, help="Seconds between snapshots (default: 60s)."
    ),
    rounds: int = typer.Option(
        60, help="Number of snapshots (default: 60 = 1 hour of data)."
    ),
) -> None:
    """Collect system metrics every N seconds for M rounds."""
    init_db()
    total_minutes = rounds * interval // 60
    console.print(
        f"\n[bold green]Starting collection:[/bold green] "
        f"{rounds} snapshots every {interval}s "
        f"([cyan]~{total_minutes} minutes total[/cyan])\n"
    )
    collect_loop(interval_seconds=interval, rounds=rounds)
    console.print(
        f"\n[bold green]Done.[/bold green] "
        f"{rounds} snapshots saved to database.\n"
    )


@app.command()
def status() -> None:
    """Show a single live snapshot of current resource usage."""
    init_db()
    snap = collect_snapshot()
    save_snapshot(snap)

    cpu   = snap["cpu_percent"]
    ram   = snap["ram_percent"]
    disk  = snap["disk_percent"]

    cpu_thresh  = METRIC_THRESHOLDS["cpu_percent"]
    ram_thresh  = METRIC_THRESHOLDS["ram_percent"]
    disk_thresh = METRIC_THRESHOLDS["disk_percent"]

    console.print("\n[bold]Current System Status[/bold]\n")
    console.print(
        f"  CPU   : [{_color(cpu, **cpu_thresh)}]{cpu:>5.1f}%[/{_color(cpu, **cpu_thresh)}]"
    )
    console.print(
        f"  RAM   : [{_color(ram, **ram_thresh)}]{ram:>5.1f}%[/{_color(ram, **ram_thresh)}]"
        f"  ({snap['ram_used_mb']:.0f} MB / {snap['ram_total_mb']:.0f} MB)"
    )
    console.print(
        f"  Disk  : [{_color(disk, **disk_thresh)}]{disk:>5.1f}%[/{_color(disk, **disk_thresh)}]"
        f"  ({snap['disk_used_gb']:.1f} GB / {snap['disk_total_gb']:.1f} GB)"
    )
    console.print(f"\n  [dim]Saved at {snap['timestamp']}[/dim]\n")


@app.command()
def watch(
    interval: int = typer.Option(5,  help="Refresh every N seconds."),
    rounds:   int = typer.Option(50, help="Stop after N refreshes."),
) -> None:
    """Live monitor — refreshes resource usage every N seconds. Ctrl+C to stop."""
    init_db()
    console.print(
        f"\n[bold]Foresight Live Monitor[/bold] — "
        f"refreshing every {interval}s. "
        f"[dim]Ctrl+C to stop.[/dim]\n"
    )

    try:
        for i in range(rounds):
            snap = collect_snapshot()
            save_snapshot(snap)

            os.system("cls")

            cpu   = snap["cpu_percent"]
            ram   = snap["ram_percent"]
            disk  = snap["disk_percent"]

            cpu_thresh  = METRIC_THRESHOLDS["cpu_percent"]
            ram_thresh  = METRIC_THRESHOLDS["ram_percent"]
            disk_thresh = METRIC_THRESHOLDS["disk_percent"]

            console.print(
                f"[bold]Foresight Live Monitor[/bold]  "
                f"[dim]{snap['timestamp']}[/dim]\n"
            )

            cpu_bar  = "█" * int(cpu  / 5)
            ram_bar  = "█" * int(ram  / 5)
            disk_bar = "█" * int(disk / 5)

            console.print(
                f"  CPU   : [{_color(cpu,  **cpu_thresh)}]{cpu:>5.1f}%[/{_color(cpu, **cpu_thresh)}]  {cpu_bar}"
            )
            console.print(
                f"  RAM   : [{_color(ram,  **ram_thresh)}]{ram:>5.1f}%[/{_color(ram, **ram_thresh)}]  {ram_bar}"
                f"  ({snap['ram_used_mb']:.0f} MB / {snap['ram_total_mb']:.0f} MB)"
            )
            console.print(
                f"  Disk  : [{_color(disk, **disk_thresh)}]{disk:>5.1f}%[/{_color(disk, **disk_thresh)}]  {disk_bar}"
                f"  ({snap['disk_used_gb']:.1f} GB / {snap['disk_total_gb']:.1f} GB)"
            )
            console.print(
                f"\n  [dim]Refresh {i+1}/{rounds} — next in {interval}s[/dim]"
            )

            if i < rounds - 1:
                time.sleep(interval)

    except KeyboardInterrupt:
        console.print("\n[yellow]Live monitor stopped.[/yellow]\n")


@app.command()
def show(
    limit: int = typer.Option(10, help="Number of recent snapshots to display."),
) -> None:
    """Show recent snapshots from the database as a color-coded table."""
    init_db()
    snapshots = get_snapshots(limit=limit)

    if not snapshots:
        console.print(
            "[yellow]No snapshots found. "
            "Run 'foresight collect' first.[/yellow]"
        )
        raise typer.Exit()

    table = Table(
        title=f"Last {len(snapshots)} Snapshots",
        box=box.ROUNDED,
        show_lines=True,
    )

    table.add_column("Timestamp",      style="cyan", no_wrap=True)
    table.add_column("CPU %",          justify="right")
    table.add_column("RAM %",          justify="right")
    table.add_column("RAM Used (MB)",  justify="right")
    table.add_column("Disk %",         justify="right")
    table.add_column("Disk Used (GB)", justify="right")

    cpu_t  = METRIC_THRESHOLDS["cpu_percent"]
    ram_t  = METRIC_THRESHOLDS["ram_percent"]
    disk_t = METRIC_THRESHOLDS["disk_percent"]

    for snap in reversed(snapshots):
        cpu  = snap["cpu_percent"]
        ram  = snap["ram_percent"]
        disk = snap["disk_percent"]

        table.add_row(
            snap["timestamp"],
            f"[{_color(cpu,  **cpu_t)}]{cpu}%[/{_color(cpu,  **cpu_t)}]",
            f"[{_color(ram,  **ram_t)}]{ram}%[/{_color(ram,  **ram_t)}]",
            str(snap["ram_used_mb"]),
            f"[{_color(disk, **disk_t)}]{disk}%[/{_color(disk, **disk_t)}]",
            str(snap["disk_used_gb"]),
        )

    console.print(table)


@app.command()
def chart(
    metric: str = typer.Option("cpu_percent", help="Metric to chart."),
    limit:  int = typer.Option(50,            help="Number of recent snapshots to plot."),
) -> None:
    """Render an ASCII line chart of a metric over time in the terminal."""
    init_db()

    if metric not in VALID_METRICS:
        console.print(f"[red]Invalid metric '{metric}'.[/red]")
        console.print(f"Valid options: {', '.join(sorted(VALID_METRICS))}")
        raise typer.Exit()

    timestamps, values = get_metric_series(metric=metric, limit=limit)

    if len(values) < 2:
        console.print(
            "[yellow]Not enough data to chart. "
            "Run 'foresight collect' first.[/yellow]"
        )
        raise typer.Exit()

    short_labels = [ts[11:16] for ts in timestamps]
    x_values     = list(range(len(values)))

    plt.clear_figure()
    plt.plot(x_values, values, label=metric, marker="braille")
    plt.title(
        f"{metric} — {short_labels[0]} to {short_labels[-1]} "
        f"({len(values)} snapshots)"
    )
    plt.xlabel("Snapshot index")
    plt.ylabel("Percent (%)")
    plt.ylim(0, 100)
    plt.plotsize(80, 20)
    plt.show()


@app.command()
def forecast(
    metric:   str = typer.Option("cpu_percent", help="Metric to forecast."),
    horizon:  str = typer.Option("30m",         help="How far ahead: '30m', '1h', '2h'."),
    model:    str = typer.Option("ensemble",    help="Model: arima, holtwinters, ensemble."),
    interval: int = typer.Option(60,            help="Your collection interval in seconds."),
) -> None:
    """Forecast future resource usage over a time horizon (e.g. 30m, 1h, 2h)."""
    init_db()

    if not _validate_inputs(metric, model):
        raise typer.Exit()

    try:
        steps = parse_horizon(horizon, interval_seconds=interval)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit()

    console.print(
        f"\n[bold]Forecasting[/bold] [cyan]{metric}[/cyan] "
        f"for next [cyan]{horizon}[/cyan] "
        f"({steps} steps × {interval}s) "
        f"using [cyan]{model.upper()}[/cyan]\n"
    )

    result = _run_forecast(metric, steps, model)

    trend_color = {"rising": "red", "falling": "green", "stable": "yellow"}.get(
        result["trend_summary"], "white"
    )

    console.print(f"  Last observed : {result['last_observed']}%")
    console.print(
        f"  Trend         : "
        f"[{trend_color}]{result['trend_summary']}[/{trend_color}]"
    )

    if "components" in result:
        console.print(
            f"\n  [dim]ARIMA        : {result['components']['arima']}[/dim]"
        )
        console.print(
            f"  [dim]Holt-Winters : {result['components']['holtwinters']}[/dim]"
        )

    thresh = METRIC_THRESHOLDS.get(metric, {"warning": 75.0, "critical": 90.0})

    console.print(f"\n  {'Time':>10}   {'Value':>8}   Chart")
    console.print(f"  {'─'*10}   {'─'*8}   {'─'*20}")

    for i, val in enumerate(result["forecast"], start=1):
        bar        = "█" * int(val / 5)
        time_label = steps_to_human_time(i, interval_seconds=interval)
        col        = _color(val, **thresh)
        console.print(
            f"  {time_label:>10} : [{col}]{val:>6.2f}%[/{col}]  {bar}"
        )

    console.print()


@app.command()
def alert(
    metric:    str   = typer.Option("cpu_percent", help="Metric to check."),
    horizon:   str   = typer.Option("30m",         help="How far ahead: '30m', '1h', '2h'."),
    threshold: float = typer.Option(-1.0,          help="Custom threshold %. Uses smart default if omitted."),
    model:     str   = typer.Option("ensemble",    help="Model: arima, holtwinters, ensemble."),
    interval:  int   = typer.Option(60,            help="Your collection interval in seconds."),
) -> None:
    """Check if a metric is predicted to breach its health threshold."""
    init_db()

    if not _validate_inputs(metric, model):
        raise typer.Exit()

    try:
        steps = parse_horizon(horizon, interval_seconds=interval)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit()

    # Apply smart default threshold if user didn't provide one
    if threshold == -1.0:
        threshold = METRIC_THRESHOLDS.get(
            metric, {"warning": 85.0}
        )["warning"]
        console.print(
            f"\n  [dim]Using smart default threshold: "
            f"{threshold}% for {metric}[/dim]"
        )

    result       = _run_forecast(metric, steps, model)
    alert_result = check_threshold(forecast_result=result, threshold=threshold)

    status = alert_result["status"]
    icon   = _status_icon(status)
    style  = _status_style(status)

    console.print(
        f"\n  {icon}  [{style}]{status.upper()}[/{style}]"
        f" — {alert_result['message']}\n"
    )

    if alert_result["breaches"]:
        console.print(f"  [dim]Predicted breaches above {threshold}%:[/dim]")
        for b in alert_result["breaches"]:
            time_label = steps_to_human_time(b["step"], interval_seconds=interval)
            console.print(
                f"    {time_label:>10} : [red]{b['value']}%[/red]"
            )
        console.print()


@app.command()
def healthcheck(
    horizon:  str = typer.Option("30m",      help="How far ahead to check: '30m', '1h', '2h'."),
    model:    str = typer.Option("ensemble", help="Model: arima, holtwinters, ensemble."),
    interval: int = typer.Option(60,         help="Your collection interval in seconds."),
) -> None:
    """Run a full health check across CPU, RAM, and Disk at once."""
    init_db()

    if model not in VALID_MODELS:
        console.print(f"[red]Invalid model. Choose: {', '.join(VALID_MODELS)}[/red]")
        raise typer.Exit()

    try:
        steps = parse_horizon(horizon, interval_seconds=interval)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit()

    metrics_to_check = [
        ("cpu_percent",  METRIC_THRESHOLDS["cpu_percent"]["warning"]),
        ("ram_percent",  METRIC_THRESHOLDS["ram_percent"]["warning"]),
        ("disk_percent", METRIC_THRESHOLDS["disk_percent"]["warning"]),
    ]

    console.print(
        f"\n[bold]System Health Check[/bold] — "
        f"next [cyan]{horizon}[/cyan] "
        f"via [cyan]{model.upper()}[/cyan]\n"
    )

    overall_status = "ok"

    for metric, threshold in metrics_to_check:
        result       = _run_forecast(metric, steps, model)
        alert_result = check_threshold(forecast_result=result, threshold=threshold)
        status       = alert_result["status"]

        # Escalate overall only upward: ok → warning → critical
        if status == "critical":
            overall_status = "critical"
        elif status == "warning" and overall_status == "ok":
            overall_status = "warning"

        icon  = _status_icon(status)
        style = _status_style(status)
        col   = _color(
            result["last_observed"],
            **METRIC_THRESHOLDS.get(metric, {"warning": 75.0, "critical": 90.0}),
        )

        console.print(
            f"  {icon}  [cyan]{metric:<20}[/cyan] "
            f"[{style}]{status.upper():<10}[/{style}]  "
            f"now: [{col}]{result['last_observed']}%[/{col}]  "
            f"threshold: {threshold}%  "
            f"trend: {result['trend_summary']}"
        )

    overall_icon  = _status_icon(overall_status)
    overall_style = _status_style(overall_status)

    console.print(
        f"\n  {overall_icon}  "
        f"Overall: [{overall_style}]{overall_status.upper()}[/{overall_style}]\n"
    )


if __name__ == "__main__":
    app()