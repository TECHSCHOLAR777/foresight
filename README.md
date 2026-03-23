<div align="center">

# 🔭 Foresight

**Predict system resource exhaustion before it happens.**

[![PyPI](https://img.shields.io/pypi/v/foresight-cli)](https://pypi.org/project/foresight-cli/)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Open Source](https://img.shields.io/badge/Open%20Source-%E2%9D%A4-red)](https://github.com/TECHSCHOLAR777/foresight)
[![Made at DTU](https://img.shields.io/badge/Made%20at-DTU%20Delhi-green)](https://dtu.ac.in)

---

*Traditional monitoring tools tell you what **is** happening.*
*Foresight tells you what **will** happen — before it does.*

---

</div>

## 📖 What is Foresight?

Foresight is a lightweight, CLI-native system resource forecaster built in Python.
It collects CPU, RAM, and disk metrics locally, stores them in SQLite, and applies
time-series ML models (ARIMA, Holt-Winters, Ensemble) to predict resource exhaustion
**before** it happens.

No cloud. No dashboard. No subscription. Just your terminal.

```bash
foresight healthcheck --horizon 1h
```

```
System Health Check — next 1h via ENSEMBLE

  ✅  cpu_percent    OK          now: 18.4%   threshold: 75.0%   trend: stable
  🚨  ram_percent    CRITICAL    now: 87.4%   threshold: 80.0%   trend: rising
  ✅  disk_percent   OK          now: 17.4%   threshold: 85.0%   trend: stable

  🚨  Overall: CRITICAL
```

---

## ✨ Features

| Feature | Description |
|---|---|
| **Live Monitor** | Real-time resource usage with color-coded health indicators |
| **ARIMA Forecasting** | AutoRegressive model for trend-based prediction |
| **Holt-Winters Forecasting** | Exponential smoothing — weights recent data more heavily |
| **Ensemble Forecasting** | Blends ARIMA + Holt-Winters for more robust predictions |
| **Threshold Alerting** | Warns when a metric is predicted to breach safe limits |
| **Health Check** | Full system overview across all metrics in one command |
| **ASCII Charts** | Visualize metric history directly in the terminal |
| **Smart Defaults** | Per-metric health thresholds based on industry standards |
| **Horizon-based** | Think in time: `--horizon 30m`, `--horizon 1h`, `--horizon 2h` |

---

## 🚀 Quick Start

### Install via pip

```bash
pip install foresight-cli
```

That's it. The `foresight` command is now available globally.

### ⚠️ Windows Users — If `foresight` is Not Recognized

This is a common Windows issue. After installing, if you see:
```
foresight : The term 'foresight' is not recognized...
```

Run this **once** in PowerShell to fix it permanently:

```powershell
[System.Environment]::SetEnvironmentVariable(
  "Path",
  $env:Path + ";$env:APPDATA\Python\Python310\Scripts",
  "User"
)
```

Then **close and reopen your terminal.** Done — works forever after that.

> 💡 Replace `Python310` with your version. Check with `python --version`.
> For example Python 3.11 → `Python311`, Python 3.12 → `Python312`.

### Collect Data

```bash
# Collect 60 snapshots every 60 seconds (1 hour of data)
foresight collect

# Quick test — 10 snapshots every 5 seconds
foresight collect --rounds 10 --interval 5
```

> ⚠️ **Important:** Forecasting requires historical data. For reliable 30-minute
> forecasts, collect at least 2-3 hours of data first. The more data, the better
> the predictions.

### Check Your System

```bash
foresight healthcheck --horizon 30m
```

---

## 📋 All Commands

### `foresight collect`
Collect system metrics and save to local SQLite database.
```bash
foresight collect                           # 60 rounds × 60s = 1 hour
foresight collect --rounds 30 --interval 5  # 30 snapshots every 5 seconds
```

### `foresight status`
Single live snapshot with color-coded health indicators.
```bash
foresight status
```

### `foresight watch`
Live refreshing monitor. Clears screen and updates every N seconds.
```bash
foresight watch                    # every 5s, 50 rounds
foresight watch --interval 2 --rounds 30
```

### `foresight show`
Display recent snapshots as a color-coded formatted table.
```bash
foresight show               # last 10 snapshots
foresight show --limit 50    # last 50 snapshots
```

### `foresight chart`
ASCII line chart of any metric rendered directly in the terminal.
```bash
foresight chart                               # default: cpu_percent
foresight chart --metric ram_percent
foresight chart --metric disk_percent --limit 100
```

**Available metrics:** `cpu_percent`, `ram_percent`, `ram_used_mb`, `disk_percent`, `disk_used_gb`

### `foresight forecast`
Forecast future resource usage over a time horizon.
```bash
foresight forecast                                     # CPU, 30m, ensemble
foresight forecast --metric ram_percent --horizon 1h
foresight forecast --metric cpu_percent --horizon 2h --model arima
foresight forecast --metric disk_percent --model holtwinters
```

**Models:**
- `ensemble` *(default)* — Blends ARIMA + Holt-Winters. Most robust.
- `arima` — Better for data with clear, consistent trends
- `holtwinters` — Better when recent data matters more than history

### `foresight alert`
Check if a metric is predicted to breach its health threshold.
```bash
foresight alert                                         # CPU, 30m, smart threshold
foresight alert --metric ram_percent --horizon 1h
foresight alert --metric cpu_percent --threshold 70     # custom threshold
```

### `foresight healthcheck`
Full system health check across CPU, RAM, and Disk at once.
```bash
foresight healthcheck              # 30m horizon, ensemble
foresight healthcheck --horizon 1h
foresight healthcheck --model arima
```

---

## 🎯 Smart Health Thresholds

Foresight uses industry-standard thresholds by default:

| Metric | Warning | Critical | Reasoning |
|---|---|---|---|
| CPU | 75% | 90% | Above 75% sustained → thermal throttling risk |
| RAM | 80% | 90% | Above 80% → heavy memory swapping begins |
| Disk | 85% | 95% | Above 85% → write performance degrades |

Override any threshold with `--threshold` flag.

---

## 📊 How Much Data Do You Need?

| Forecast Horizon | Minimum Snapshots | Recommended |
|---|---|---|
| 30 minutes | 30 snapshots | 2–3 hours of data |
| 1 hour | 60 snapshots | 4–6 hours of data |
| 2 hours | 120 snapshots | 8–12 hours of data |

**Rule of thumb:** Collect at least 3–5× more history than your forecast horizon
for reliable predictions.

---

## 🧠 How Forecasting Works

Foresight uses three time-series forecasting models:

**ARIMA (AutoRegressive Integrated Moving Average)**
Predicts future values based on patterns in past values and past prediction errors.
Parameters: AR (past values), I (differencing to remove trend), MA (error correction).
Best for data with a clear, consistent long-term trend.

**Holt-Winters Exponential Smoothing**
Weights recent data more heavily than older data — exponentially decreasing influence.
The model continuously updates its estimate of level and trend as new data arrives.
Best for data where recent behaviour matters more than long-term history.

**Ensemble (Default)**
Averages ARIMA and Holt-Winters predictions step by step. Two models with different
assumptions tend to make different errors — averaging cancels individual mistakes out.
Consistently more robust than either model alone.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| Metrics collection | psutil |
| Local storage | SQLite (built-in) |
| Forecasting | statsmodels (ARIMA + Holt-Winters) |
| Data handling | pandas |
| CLI framework | Typer |
| Terminal UI | Rich |
| ASCII charts | plotext |
| Packaging | setuptools + pyproject.toml |

---

## 📁 Project Structure

```
foresight/
├── foresight/
│   ├── __init__.py
│   ├── collector.py    # psutil metrics collection
│   ├── storage.py      # SQLite database layer
│   ├── forecaster.py   # ARIMA, Holt-Winters, Ensemble, alerting
│   └── cli.py          # Typer CLI — all 8 commands
├── tests/
├── data/               # SQLite database (gitignored, created locally)
├── pyproject.toml
├── requirements.txt
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

---

## 🤝 Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

---

## 🗺️ Roadmap

- [ ] Export forecasts to CSV
- [ ] Cron job integration for automated collection
- [ ] Network metrics (bandwidth usage)
- [ ] Multi-machine support
- [ ] Weighted ensemble based on historical model accuracy
- [ ] GitHub Actions CI pipeline
- [ ] Seasonal detection when sufficient data is available

---

## 👨‍💻 Author

Built by **Rishi Garg**
BTech, Software Engineering (Batch of 2029), Delhi Technological University,
Member @[AIMS-DTU](https://aimsdtu.in) — AI/ML Society of DTU

*Built as a portfolio and learning project with a focus on
time-series forecasting, system programming, and open-source contribution.*

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

**If this helped you, give it a ⭐ on GitHub**

</div>
