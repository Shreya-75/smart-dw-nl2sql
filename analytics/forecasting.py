"""
Time-series forecasting for the Olist data warehouse.

Uses sklearn LinearRegression fit on a month-index feature (handles trend)
plus sin/cos features (handles 12-month seasonality). Produces 6-month
point forecasts with a ±1 std confidence band.

Input:  DataFrame with one time column (year/month/date) + one numeric column
Output: ForecastResult with actuals and predictions merged into a single df
        ready for plotting in chart_builder or Dashboard.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass
class ForecastResult:
    df:          pd.DataFrame   # combined actuals + forecast; 'is_forecast' bool col
    metric_col:  str
    time_col:    str
    n_forecast:  int
    r2:          float          # training R² (0–1 quality indicator)
    next_label:  str            # e.g. "Jan 2019"
    next_value:  float          # point estimate for first forecast period
    pct_change:  float          # vs last actual (fraction, +ve = growth)


def _make_features(idx: np.ndarray) -> np.ndarray:
    """Month-index + two seasonality harmonics → feature matrix."""
    period = 12.0
    return np.column_stack([
        idx,
        np.sin(2 * np.pi * idx / period),
        np.cos(2 * np.pi * idx / period),
    ])


def forecast_series(
    df: pd.DataFrame,
    time_col: str,
    metric_col: str,
    n_periods: int = 6,
) -> ForecastResult | None:
    """
    Fit a linear trend + seasonality model and extend the series by n_periods.

    Returns None if the series is too short (< 6 data points) to be meaningful.
    """
    from sklearn.linear_model import Ridge
    from sklearn.metrics import r2_score

    df = df.copy().sort_values(time_col).reset_index(drop=True)
    df[metric_col] = pd.to_numeric(df[metric_col], errors="coerce")
    df = df.dropna(subset=[metric_col])

    if len(df) < 6:
        return None

    n = len(df)
    idx = np.arange(n, dtype=float)
    X   = _make_features(idx)
    y   = df[metric_col].values.astype(float)

    model = Ridge(alpha=1.0)
    model.fit(X, y)
    y_pred_train = model.predict(X)
    r2 = float(r2_score(y, y_pred_train))

    # Forecast future periods
    fut_idx = np.arange(n, n + n_periods, dtype=float)
    X_fut   = _make_features(fut_idx)
    y_fut   = model.predict(X_fut)
    y_fut   = np.maximum(y_fut, 0)  # revenue can't be negative

    # Confidence band: ± residual std
    residuals = y - y_pred_train
    std       = float(residuals.std())

    # Build label column for future periods
    last_label = str(df[time_col].iloc[-1])
    fut_labels = _extend_labels(df[time_col].tolist(), n_periods)

    actuals_df = df[[time_col, metric_col]].copy()
    actuals_df["is_forecast"]  = False
    actuals_df["forecast_low"] = np.nan
    actuals_df["forecast_hi"]  = np.nan

    forecast_df = pd.DataFrame({
        time_col:        fut_labels,
        metric_col:      y_fut,
        "is_forecast":   True,
        "forecast_low":  np.maximum(y_fut - std, 0),
        "forecast_hi":   y_fut + std,
    })

    combined = pd.concat([actuals_df, forecast_df], ignore_index=True)

    last_actual = float(y[-1])
    next_val    = float(y_fut[0])
    pct_change  = (next_val - last_actual) / last_actual if last_actual else 0.0

    return ForecastResult(
        df=combined,
        metric_col=metric_col,
        time_col=time_col,
        n_forecast=n_periods,
        r2=r2,
        next_label=str(fut_labels[0]),
        next_value=next_val,
        pct_change=pct_change,
    )


def _extend_labels(labels: list, n: int) -> list:
    """Infer and extend time labels (handles 'YYYY-MM', 'YYYY', integers)."""
    if not labels:
        return [f"T+{i+1}" for i in range(n)]

    last = str(labels[-1])

    # YYYY-MM format
    if len(last) == 7 and "-" in last:
        try:
            base = pd.Period(last, freq="M")
            return [(base + i + 1).strftime("%Y-%m") for i in range(n)]
        except Exception:
            pass

    # Pure integer year
    try:
        yr = int(last)
        return [str(yr + i + 1) for i in range(n)]
    except ValueError:
        pass

    # Numeric month index
    try:
        m = int(float(last))
        return [str(m + i + 1) for i in range(n)]
    except ValueError:
        pass

    return [f"{last}+{i+1}" for i in range(n)]
