# Contributing to Foresight

Thank you for considering a contribution. This is a learning-focused
open-source project and all contributions are welcome — from bug fixes
to new features to documentation improvements.

---

## Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/foresight.git
   cd foresight
   ```
3. Create a virtual environment and install:
   ```bash
   python -m venv venv
   venv\Scripts\activate    # Windows
   source venv/bin/activate  # Mac/Linux
   pip install -r requirements.txt
   pip install -e .
   ```
4. Create a new branch for your feature:
   ```bash
   git checkout -b feature/your-feature-name
   ```

---

## Project Structure

Before contributing, understand what each file does:

| File | Responsibility |
|---|---|
| `collector.py` | OS-level metric collection via psutil |
| `storage.py` | SQLite read/write operations |
| `forecaster.py` | ML models, alerting, time utilities |
| `cli.py` | All CLI commands via Typer + Rich |

**One concern per file. Keep it that way.**

---

## Contribution Guidelines

### Code Style
- Python 3.10+
- Type hints on all function signatures
- Private helpers prefixed with `_`
- Constants in `ALL_CAPS`
- Maximum line length: 88 characters

### What We Welcome
- Bug fixes with clear explanation of root cause
- New forecasting models (must match existing return dict shape)
- New CLI commands (must follow existing Typer pattern)
- Documentation improvements
- Performance improvements with benchmarks
- Tests in the `tests/` directory

### What We Won't Merge
- Changes that break the consistent interface pattern
  (all forecast functions must return identical dict shape)
- Dependencies that require C++ compilation on Windows
- Features that require a running server or cloud connection
- Code without type hints

---

## Adding a New Forecasting Model

All forecast functions must return this exact dict shape:

```python
{
    "metric": str,
    "model": str,
    "order": tuple | None,
    "last_observed": float,
    "steps_ahead": int,
    "forecast": list[float],        # values clamped 0.0–100.0
    "trend_summary": str,           # "rising" | "falling" | "stable"
}
```

Use the existing helpers — don't reimplement them:
- `_validate_metric(metric)` — validates against VALID_METRICS
- `_load_series(metric, limit)` — fetches from DB, returns pd.Series
- `_describe_trend(forecast_values)` — returns trend string

---

## Submitting a Pull Request

1. Make sure your code runs without errors
2. Test all 8 CLI commands manually
3. Update `README.md` if you added a command or changed behaviour
4. Write a clear PR description:
   - What problem does this solve?
   - How did you solve it?
   - What did you test?

---

## Reporting Issues

Open a GitHub Issue with:
- Your OS and Python version (`python --version`)
- The exact command you ran
- The full error traceback (paste it completely)
- What you expected to happen

---

## Questions?

Open a Discussion on GitHub. This project was built as a learning
exercise and the maintainer is happy to discuss architecture decisions,
explain code, or help you understand how to contribute.
