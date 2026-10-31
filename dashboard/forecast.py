"""Short-range projections for annual series, with an honest track record.

Each series has 10-25 yearly points, so the models are deliberately simple and explainable:

  * naive  -- next years equal the last value (the baseline every model must beat);
  * drift  -- the last value plus the average yearly change over the fit window;
  * linear -- a straight-line (least-squares) trend over the fit window;
  * holt   -- Holt's linear exponential smoothing: a level and a trend that follow recent
              years more than old ones (smoothing weights chosen by grid search).

Every model is backtested the same way (rolling origin): fit on the first k years, forecast the
next 1-5, compare with what was actually published, repeat for every k. The model with the lowest
average error is used. Prediction intervals come from that model's backtest errors at each
horizon, so they reflect how wrong this method has really been on this series.

Plain Python on purpose: the models are a few lines each, and the whole computation is visible
and testable without numpy/statsmodels. Never let an LLM produce these numbers.
"""
import math

HORIZON = 5          # never project further than 5 years
MIN_POINTS = 8       # fewest consecutive annual values worth forecasting
MIN_TRAIN = 6        # fewest values a backtest fit may use
Z80, Z95 = 1.2816, 1.9600

MODEL_INFO = {
    "naive": ("Naive (last value)", "Assumes every future year equals the last published value."),
    "drift": ("Drift", "Continues the average yearly change between the first and last year of the fit window."),
    "linear": ("Linear trend", "Fits a straight line through the fit window and extends it."),
    "holt": ("Holt's exponential smoothing",
             "Tracks a level and a trend, weighting recent years more heavily than older ones."),
}
BOUNDS = {"percent": (0.0, 100.0), "millions": (0.0, None), "per_household_year": (0.0, None)}


def naive(values, horizon):
    return [values[-1]] * horizon


def drift(values, horizon):
    step = (values[-1] - values[0]) / (len(values) - 1)
    return [values[-1] + step * h for h in range(1, horizon + 1)]


def linear(values, horizon):
    n = len(values)
    x_mean, y_mean = (n - 1) / 2, sum(values) / n
    sxx = sum((x - x_mean) ** 2 for x in range(n))
    slope = sum((x - x_mean) * (y - y_mean) for x, y in zip(range(n), values)) / sxx
    intercept = y_mean - slope * x_mean
    return [intercept + slope * (n - 1 + h) for h in range(1, horizon + 1)]


GRID = [i / 20 for i in range(1, 20)]  # 0.05 ... 0.95


def _holt_run(values, alpha, beta):
    """Smooth the series; returns (final level, final trend, sum of squared one-step errors)."""
    level, trend, sse = values[0], values[1] - values[0], 0.0
    for y in values[1:]:
        predicted = level + trend
        sse += (y - predicted) ** 2
        new_level = alpha * y + (1 - alpha) * predicted
        trend = beta * (new_level - level) + (1 - beta) * trend
        level = new_level
    return level, trend, sse


def holt_params(values):
    """The (alpha, beta) pair with the smallest one-step-ahead squared error."""
    return min(((a, b) for a in GRID for b in GRID), key=lambda ab: _holt_run(values, *ab)[2])


def holt(values, horizon):
    level, trend, _ = _holt_run(values, *holt_params(values))
    return [level + trend * h for h in range(1, horizon + 1)]


MODELS = {"naive": naive, "drift": drift, "linear": linear, "holt": holt}


def backtest(values, model, horizon=HORIZON, min_train=MIN_TRAIN):
    """{h: [(actual, predicted), ...]} from rolling-origin forecasts within `values`."""
    pairs = {h: [] for h in range(1, horizon + 1)}
    for k in range(min_train, len(values)):
        predicted = MODELS[model](values[:k], horizon)
        for h in range(1, horizon + 1):
            if k + h - 1 < len(values):
                pairs[h].append((values[k + h - 1], predicted[h - 1]))
    return pairs


def errors(pairs):
    """Overall MAE, MAPE (None if an actual is 0) and per-horizon RMSE from backtest pairs."""
    flat = [p for h in pairs for p in pairs[h]]
    mae = sum(abs(a - p) for a, p in flat) / len(flat)
    mape = (100 * sum(abs(a - p) / abs(a) for a, p in flat) / len(flat)
            if all(a for a, _ in flat) else None)
    rmse = {h: math.sqrt(sum((a - p) ** 2 for a, p in pairs[h]) / len(pairs[h]))
            for h in pairs if pairs[h]}
    return {"mae": mae, "mape": mape, "rmse": rmse, "count": len(flat)}


def fit_window(years, values, breaks):
    """The years to fit on, and why.

    Uses the trailing run of consecutive years (gaps are never filled in), starting after the
    latest methodology break that still leaves MIN_POINTS values. Later breaks it can't avoid are
    returned so the page can flag them.
    """
    start = len(years) - 1
    while start > 0 and years[start - 1] == years[start] - 1:
        start -= 1
    years, values = years[start:], values[start:]
    if len(years) < MIN_POINTS:
        return None
    crossed = sorted(b for b in breaks if years[0] < b <= years[-1])
    usable = [b for b in crossed if years[-1] - b + 1 >= MIN_POINTS]
    if usable:
        cut = years.index(usable[-1])
        years, values = years[cut:], values[cut:]
    return {
        "years": years,
        "values": values,
        "after_break": usable[-1] if usable else None,
        "crossed": [b for b in crossed if b > years[0]],
    }


def forecast(years, values, unit, breaks=(), horizon=HORIZON):
    """A projection for an annual series, or {"reason": ...} when it can't be made responsibly."""
    window = fit_window(list(years), list(values), breaks)
    if window is None:
        return {"reason": f"Projections need at least {MIN_POINTS} consecutive annual values; "
                          "this series has fewer, so none is shown."}
    fit = window["values"]
    scores, tests = {}, {}
    for name in MODELS:
        tests[name] = backtest(fit, name, horizon)
        if any(tests[name].values()):
            scores[name] = errors(tests[name])
    best = min(scores, key=lambda m: scores[m]["mae"])
    rmse = scores[best]["rmse"]

    # Interval half-widths from the chosen model's backtest error at each horizon. With fewer than
    # 3 errors at a horizon, grow the 1-year error like a random walk; never let a band narrow.
    spreads = []
    for h in range(1, horizon + 1):
        s = rmse[h] if len(tests[best][h]) >= 3 else rmse[1] * math.sqrt(h)
        spreads.append(max(s, spreads[-1]) if spreads else s)

    low, high = BOUNDS.get(unit, (None, None))

    def clamp(v):
        if low is not None:
            v = max(low, v)
        if high is not None:
            v = min(high, v)
        return v

    last = window["years"][-1]
    points = []
    for h, value in enumerate(MODELS[best](fit, horizon), start=1):
        s = spreads[h - 1]
        points.append({
            "year": last + h,
            "value": clamp(value),
            "lo80": clamp(value - Z80 * s), "hi80": clamp(value + Z80 * s),
            "lo95": clamp(value - Z95 * s), "hi95": clamp(value + Z95 * s),
        })
    naive_mae = scores["naive"]["mae"]
    return {
        "model": best,
        "model_name": MODEL_INFO[best][0],
        "model_description": MODEL_INFO[best][1],
        "holt_params": holt_params(fit) if best == "holt" else None,
        "fit_years": [window["years"][0], last],
        "after_break": window["after_break"],
        "crossed_breaks": window["crossed"],
        "points": points,
        "backtest": [
            {"model": m, "name": MODEL_INFO[m][0], "mae": s["mae"], "mape": s["mape"],
             "vs_naive": s["mae"] / naive_mae if naive_mae else None, "forecasts": s["count"],
             "chosen": m == best}
            for m, s in sorted(scores.items(), key=lambda kv: kv[1]["mae"])
        ],
        "beats_naive": best != "naive",
    }
