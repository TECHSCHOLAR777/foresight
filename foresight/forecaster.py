import warnings
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from foresight.storage import get_metric_series, VALID_METRICS
from statsmodels.tsa.holtwinters import ExponentialSmoothing
warnings.filterwarnings("ignore")

MINIMUM_DATA_POINTS = 20


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

    series = pd.Series(values)
    return series


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

    last_value = round(float(series.iloc[-1]), 2)
    trend = _describe_trend(forecast_values)

    return {
        "metric": metric,
        "model": "ARIMA",
        "order": order,
        "last_observed": last_value,
        "steps_ahead": steps,
        "forecast": forecast_values,
        "trend_summary": trend,
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

    last_value = round(float(series.iloc[-1]), 2)
    trend = _describe_trend(forecast_values)

    return {
        "metric": metric,
        "model": "Holt-Winters",
        "order": None,
        "last_observed": last_value,
        "steps_ahead": steps,
        "forecast": forecast_values,
        "trend_summary": trend,
    }
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


if __name__ == "__main__":
    result = forecast_arima(metric="cpu_percent", steps=10)
    print(f"\nMetric     : {result['metric']}")
    print(f"Model      : {result['model']} {result['order']}")
    print(f"Last seen  : {result['last_observed']}%")
    print(f"Trend      : {result['trend_summary']}")
    print(f"Forecast   : {result['forecast']}")


