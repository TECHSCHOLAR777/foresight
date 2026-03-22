import warnings
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from foresight.storage import get_metric_series, VALID_METRICS

warnings.filterwarnings("ignore")

MINIMUM_DATA_POINTS = 20


# ─── Private Helpers ──────────────────────────────────────────────────────────

def _validate_metric(metric: str) -> None:
    if metric not in VALID_METRICS:
        raise ValueError(
            f"Invalid metric '{metric}'. "
            f"Choose from: {VALID_METRICS}"
        )


def _load_series(metric: str, limit: int) -> pd.Series:
    timestamps, values = get_metric_series(metric=metric, limit=limit)

    if len(values) < MINIMUM_DATA_POINTS:
        raise ValueError(
            f"Not enough data. Need at least {MINIMUM_DATA_POINTS} "
            f"snapshots, got {len(values)}. "
            f"Run 'foresight collect' to gather more data."
        )
    # Soft warning — good forecast needs 3x the requested limit
    if len(values) < limit * 0.5:
        import warnings
        warnings.warn(
            f"Only {len(values)} snapshots available. "
            f"Forecasts improve significantly with more data. "
            f"Run 'foresight collect --rounds 60' for best results.",
            UserWarning,
            stacklevel=2,
        )

    return pd.Series(values)


def _describe_trend(forecast_values: list[float]) -> str:
    first = forecast_values[0]
    last = forecast_values[-1]
    delta = last - first

    if delta > 5:
        return "rising"
    elif delta < -5:
        return "falling"
    else:
        return "stable"


# ─── Forecasting Models ───────────────────────────────────────────────────────

def forecast_arima(
    metric: str = "cpu_percent",
    steps: int = 10,
    limit: int = 100,
    order: tuple = (2, 1, 1),
) -> dict:
    _validate_metric(metric)
    series = _load_series(metric=metric, limit=limit)

    model = ARIMA(series, order=order)
    fitted = model.fit()

    forecast_result = fitted.forecast(steps=steps)
    forecast_values = [round(float(v), 2) for v in forecast_result]
    forecast_values = [max(0.0, min(100.0, v)) for v in forecast_values]

    return {
        "metric": metric,
        "model": "ARIMA",
        "order": order,
        "last_observed": round(float(series.iloc[-1]), 2),
        "steps_ahead": steps,
        "forecast": forecast_values,
        "trend_summary": _describe_trend(forecast_values),
    }


def forecast_holtwinters(
    metric: str = "cpu_percent",
    steps: int = 10,
    limit: int = 100,
) -> dict:
    _validate_metric(metric)
    series = _load_series(metric=metric, limit=limit)

    model = ExponentialSmoothing(
        series,
        trend="add",
        seasonal=None,
        initialization_method="estimated",
    )

    fitted = model.fit(optimized=True)
    forecast_result = fitted.forecast(steps=steps)

    forecast_values = [
        round(max(0.0, min(100.0, float(v))), 2)
        for v in forecast_result
    ]

    return {
        "metric": metric,
        "model": "Holt-Winters",
        "order": None,
        "last_observed": round(float(series.iloc[-1]), 2),
        "steps_ahead": steps,
        "forecast": forecast_values,
        "trend_summary": _describe_trend(forecast_values),
    }


def forecast_ensemble(
    metric: str = "cpu_percent",
    steps: int = 10,
    limit: int = 100,
) -> dict:
    _validate_metric(metric)

    arima_result = forecast_arima(metric=metric, steps=steps, limit=limit)
    hw_result = forecast_holtwinters(metric=metric, steps=steps, limit=limit)

    blended = [
        round(max(0.0, min(100.0, (a + b) / 2)), 2)
        for a, b in zip(arima_result["forecast"], hw_result["forecast"])
    ]

    return {
        "metric": metric,
        "model": "Ensemble (ARIMA + Holt-Winters)",
        "order": None,
        "last_observed": arima_result["last_observed"],
        "steps_ahead": steps,
        "forecast": blended,
        "trend_summary": _describe_trend(blended),
        "components": {
            "arima": arima_result["forecast"],
            "holtwinters": hw_result["forecast"],
        },
    }


# ─── Alerting ─────────────────────────────────────────────────────────────────

def check_threshold(
    forecast_result: dict,
    threshold: float = 85.0,
) -> dict:
    forecast_values = forecast_result["forecast"]
    metric = forecast_result["metric"]
    last_observed = forecast_result["last_observed"]

    breaches = [
        {"step": i + 1, "value": v}
        for i, v in enumerate(forecast_values)
        if v >= threshold
    ]

    already_critical = last_observed >= threshold

    if already_critical:
        status = "critical"
        message = (
            f"{metric} is ALREADY at {last_observed}% — "
            f"above threshold of {threshold}%"
        )
    elif breaches:
        first_breach = breaches[0]
        status = "warning"
        message = (
            f"{metric} predicted to reach {first_breach['value']}% "
            f"in {steps_to_human_time(first_breach['step'])} "
            f"(threshold: {threshold}%)"
        )
    else:
        status = "ok"
        message = (
            f"{metric} looks safe — "
            f"no breach predicted within {len(forecast_values)} steps "
            f"(threshold: {threshold}%)"
        )

    return {
        "metric": metric,
        "threshold": threshold,
        "status": status,
        "message": message,
        "breaches": breaches,
        "already_critical": already_critical,
    }


# ─── Time Utilities ───────────────────────────────────────────────────────────

def steps_to_human_time(step: int, interval_seconds: int = 60) -> str:
    total_seconds = step * interval_seconds
    total_minutes = total_seconds // 60

    if total_minutes < 1:
        return f"~{total_seconds}s"
    elif total_minutes < 60:
        return f"~{total_minutes}m"
    else:
        hours = total_minutes // 60
        minutes = total_minutes % 60
        if minutes == 0:
            return f"~{hours}h"
        return f"~{hours}h {minutes}m"


def parse_horizon(horizon: str, interval_seconds: int = 60) -> int:
    horizon = horizon.strip().lower()

    if horizon.endswith("h"):
        hours = float(horizon[:-1])
        total_seconds = hours * 3600
    elif horizon.endswith("m"):
        minutes = float(horizon[:-1])
        total_seconds = minutes * 60
    else:
        raise ValueError(
            f"Invalid horizon '{horizon}'. "
            f"Use format: '30m' for 30 minutes or '2h' for 2 hours."
        )

    steps = max(1, int(total_seconds // interval_seconds))
    return steps


if __name__ == "__main__":
    result = forecast_arima(metric="cpu_percent", steps=10)
    print(f"\nMetric   : {result['metric']}")
    print(f"Model    : {result['model']} {result['order']}")
    print(f"Last seen: {result['last_observed']}%")
    print(f"Trend    : {result['trend_summary']}")
    print(f"Forecast : {result['forecast']}")

