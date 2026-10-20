"""Run after analysis.py to independently verify the saved inputs and results."""
from pathlib import Path
from math import isclose
import pandas as pd

ROOT = Path(__file__).resolve().parent
data = pd.read_csv(ROOT / "data/revenue_2026_07_09.csv", parse_dates=["date"])
predictions = pd.read_csv(ROOT / "results/daily_revenue_backtest_predictions.csv", parse_dates=["date"])
metrics = pd.read_csv(ROOT / "results/daily_revenue_backtest_mae.csv", index_col="method")

calendar = pd.date_range("2026-07-01", "2026-09-30")
closures = pd.to_datetime(["2026-07-12", "2026-07-13"])
assert len(data) == 90 and data["date"].is_unique
assert pd.DatetimeIndex(data["date"]).equals(calendar.difference(closures))
assert data["revenue"].notna().all()
assert data.groupby(data["date"].dt.month)["revenue"].sum().to_dict() == {
    7: 12851.5, 8: 13754.0, 9: 16222.0,
}
assert pd.DatetimeIndex(predictions["date"]).equals(pd.date_range("2026-09-01", "2026-09-30"))
assert predictions["in_common_evaluation"].all()

# Recompute each forecast from the raw data using strictly earlier dates.
for _, prediction in predictions.iterrows():
    target = prediction["date"]
    history = data.loc[data["date"] < target].sort_values("date")
    same_weekday = history["date"].dt.dayofweek.eq(target.dayofweek)
    same_type = history["date"].dt.dayofweek.ge(5).eq(target.dayofweek >= 5)
    selected = {
        "A": history.tail(7),
        "B": history.loc[same_weekday].tail(4),
        "C": history.loc[same_type].tail(4),
    }
    actual = data.loc[data["date"].eq(target), "revenue"].iloc[0]
    assert prediction["actual_recorded_CNY"] == actual
    for method, sample in selected.items():
        assert sample["date"].lt(target).all()
        assert prediction[f"{method}_status"] == "ok"
        assert prediction[f"{method}_history_n"] == len(sample)
        assert prediction[f"{method}_history_dates"] == "|".join(sample["date"].dt.strftime("%Y-%m-%d"))
        expected = sample["revenue"].mean()
        assert isclose(prediction[f"{method}_pred_CNY"], expected, abs_tol=1e-10)
        assert isclose(prediction[f"{method}_absolute_error_CNY"], abs(expected - actual), abs_tol=1e-10)

for method in ["A", "B", "C"]:
    for group, mask in {
        "overall": predictions["in_common_evaluation"],
        "weekday": predictions["date"].dt.dayofweek.lt(5),
        "weekend": predictions["date"].dt.dayofweek.ge(5),
    }.items():
        actual = predictions.loc[mask, "actual_recorded_CNY"]
        forecast = predictions.loc[mask, f"{method}_pred_CNY"]
        assert metrics.loc[method, f"{group}_days"] == len(actual)
        assert isclose(metrics.loc[method, f"{group}_MAE_CNY"], (forecast - actual).abs().mean(), abs_tol=1e-10)

expected_figures = {
    "01_daily_revenue.png", "02_overall_boxplot.png", "03_monthly_mean_revenue.png",
    "04_monthly_boxplots.png", "05_backtest_mae.png",
}
assert {p.name for p in (ROOT / "figures").glob("*.png")} == expected_figures
for name in expected_figures:
    assert (ROOT / "figures" / name).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")

print("PASS: 90 records; monthly totals and closures; 90 forecasts with strictly earlier histories;")
print("30 common evaluation dates; grouped MAE; five saved PNG figures.")
