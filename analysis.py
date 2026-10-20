# -*- coding: utf-8 -*-
# 早餐店收入分析与逐日预测回测：2026 年 7—9 月
# 在 PyCharm 中打开本文件，右键编辑区，选择 Run 即可运行。
# 所需依赖：python -m pip install -r requirements.txt
# 运行后保存 5 张图和 CSV 表格，最后统一显示图表；--no-show 仅保存不弹窗。
#
# 收入包含实际电子收款和估算现金，未包含支付宝；金额单位为 CNY。
# 两天台风停业不计入营业日均值，不填零、不插值、不修改原始金额。
# 工作日仅按周一至周五分类，不代表实际出勤，也未按节假日或调休调整。
# 上班、上学及 9 月开学带动需求仅是待检验解释，不认定为原因。
# 使用三种简单历史均值进行回测，不使用机器学习；结果说明由实际计算值生成。

from pathlib import Path
import argparse
import matplotlib
import pandas as pd

parser = argparse.ArgumentParser(description="Breakfast shop revenue analysis and September backtest")
parser.add_argument("--no-show", action="store_true", help="Save all outputs without opening plot windows")
args = parser.parse_args()
if args.no_show:
    matplotlib.use("Agg")
import matplotlib.pyplot as plt

# 只调整表格显示，不改变计算使用的数值。
pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 20)

# %% 0. 读取原始记录，检查日期和月度合计；不更改金额
# 路径始终以脚本所在文件夹为准，PyCharm 的工作目录不影响读取。
ROOT = Path(__file__).resolve().parent
FIGURES_DIR = ROOT / "figures"
RESULTS_DIR = ROOT / "results"
FIGURES_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)
df = pd.read_csv(ROOT / "data" / "revenue_2026_07_09.csv", parse_dates=["date"])

# 添加后续分析需要的分类
df["month"] = df["date"].dt.strftime("%Y-%m")
df["weekday"] = df["date"].dt.dayofweek  # 周一=0，周日=6
df["is_weekend"] = df["weekday"] >= 5

assert len(df) == 90, "记录数应为 90，请检查数据录入。"
assert not df["date"].duplicated().any(), "发现重复日期"

# 核对每月记录数、总金额、日均金额
summary = df.groupby("month")["revenue"].agg(
    days="count",
    total="sum",
    daily_average="mean"
)

expected_totals = pd.Series({"2026-07": 12851.50, "2026-08": 13754.00, "2026-09": 16222.00})
assert summary["total"].sub(expected_totals).abs().lt(0.001).all(), "月度合计与原始资料不符。"
print(f"共 {len(df)} 条每日记录；月度合计核对通过。")
print(summary.round(2))


# %% 1. 每日收入如何变化？停业日期是否保留为断点？
print("\n—— 1. 每日收入变化 ——")
# 使用副本，原始 df 保持不变
data = df[["date", "revenue", "month", "weekday", "is_weekend"]].copy()
data = data.sort_values("date")

assert data["date"].is_unique, "存在重复日期，请先核查。"
assert data["revenue"].notna().all(), "营业日收入有缺失，请先核查。"
assert data["month"].eq(data["date"].dt.strftime("%Y-%m")).all(), "month 与日期不一致。"
assert data["weekday"].eq(data["date"].dt.dayofweek).all(), "weekday 与日期不一致。"
assert data["is_weekend"].eq(data["weekday"].ge(5)).all(), "is_weekend 与星期不一致。"

# 这里的工作日仅指周一至周五，未按节假日或调休调整
day_order = ["Weekday", "Weekend"]
day_names = {"Weekday": "工作日", "Weekend": "周末"}
data["day_type"] = data["is_weekend"].map({
    False: "Weekday",
    True: "Weekend"
})

calendar = pd.date_range("2026-07-01", "2026-09-30", freq="D")
closed = pd.to_datetime(["2026-07-12", "2026-07-13"])

assert pd.DatetimeIndex(data["date"]).equals(
    calendar.difference(closed)
), "记录日期与预期营业日不一致。"

# 不填零、不插值
daily = data.set_index("date")["revenue"].reindex(calendar)

fig, ax = plt.subplots(figsize=(12, 4))
ax.plot(daily.index, daily, marker="o", markersize=3, linewidth=1.2)

ax.axvspan(
    closed[0] - pd.Timedelta(hours=12),
    closed[1] + pd.Timedelta(hours=12),
    color="gray",
    alpha=0.2,
    label="Closed: Jul 12–13"
)

ax.set(
    title="Daily Revenue: July–September 2026",
    xlabel="Date",
    ylabel="Revenue (CNY)"
)
ax.grid(axis="y", alpha=0.25)
ax.legend()
fig.autofmt_xdate()
fig.tight_layout()
fig.savefig(FIGURES_DIR / "01_daily_revenue.png", dpi=160, bbox_inches="tight")

print(f"绘图日历共 {len(daily)} 天，有收入记录 {daily.notna().sum()} 天。")
print("断点日期：", daily.index[daily.isna()].strftime("%Y-%m-%d").tolist())

# %% 2. 工作日与周末的收入水平和波动有何不同？
# std 为样本标准差（ddof=1）；箱线图须线外的点照常保留。
print("\n—— 2. 工作日与周末的收入分布 ——")
overall = (
    data.groupby("day_type")["revenue"]
    .agg(days="count", mean="mean", median="median", std="std")
    .reindex(day_order)
)

# 仅显示时四舍五入，后续计算仍使用未取整的数据
print(
    overall.rename(
        index=day_names,
        columns={
            "days": "营业天数",
            "mean": "日均收入(CNY)",
            "median": "中位数(CNY)",
            "std": "样本标准差(CNY)"
        }
    ).round(2).to_string()
)

fig, ax = plt.subplots(figsize=(6, 4))
ax.boxplot(
    [data.loc[data["day_type"].eq(g), "revenue"] for g in day_order],
    positions=[1, 2],
    widths=0.5,
    showfliers=True
)
ax.set_xticks([1, 2], day_order)
ax.set(
    title="Revenue Distribution: Weekdays vs Weekends",
    ylabel="Revenue (CNY)"
)
ax.grid(axis="y", alpha=0.25)
fig.tight_layout()
fig.savefig(FIGURES_DIR / "02_overall_boxplot.png", dpi=160, bbox_inches="tight")

mean_gap = overall.loc["Weekday", "mean"] - overall.loc["Weekend", "mean"]
median_gap = overall.loc["Weekday", "median"] - overall.loc["Weekend", "median"]
std_gap = overall.loc["Weekday", "std"] - overall.loc["Weekend", "std"]

print("以下差额均为“工作日 − 周末”；正数表示工作日较高，负数表示周末较高。")
print(f"日均收入差：{mean_gap:+.2f} CNY")
print(f"中位数差：{median_gap:+.2f} CNY")
print(f"样本标准差差额：{std_gap:+.2f} CNY")

# %% 3. 各个月份的工作日和周末收入是否存在差异？
# 比较营业日均值，避免把两组营业天数的差异当成收入水平的差异。
print("\n—— 3. 按月比较工作日与周末 ——")
months = ["2026-07", "2026-08", "2026-09"]

monthly_stats = (
    data.groupby(["month", "day_type"])["revenue"]
    .agg(days="count", mean="mean", median="median")
    .reindex(
        pd.MultiIndex.from_product(
            [months, day_order],
            names=["month", "day_type"]
        )
    )
)

monthly_display = monthly_stats.rename(
    index=day_names,
    level="day_type"
)

print(
    monthly_display.rename(columns={
        "days": "营业天数",
        "mean": "日均收入(CNY)",
        "median": "中位数(CNY)"
    }).round(2).to_string()
)

monthly_means = (
    monthly_stats["mean"]
    .unstack("day_type")
    .reindex(columns=day_order)
)

ax = monthly_means.plot(
    kind="bar",
    figsize=(8, 4),
    color=["#2563A6", "#DE8F32"],
    rot=0
)
ax.set(
    title="Mean Daily Revenue by Month and Day Type",
    xlabel="Month",
    ylabel="Mean Daily Revenue (CNY)"
)
ax.legend(title="Day type")
ax.grid(axis="y", alpha=0.25)
ax.margins(y=0.2)

for bars in ax.containers:
    ax.bar_label(bars, fmt="%.2f", padding=3)

ax.figure.tight_layout()
ax.figure.savefig(FIGURES_DIR / "03_monthly_mean_revenue.png", dpi=160, bbox_inches="tight")

for month in months:
    gap = (
        monthly_means.loc[month, "Weekday"]
        - monthly_means.loc[month, "Weekend"]
    )
    print(f"{month}：工作日日均减周末日均 = {gap:+.2f} CNY。")

# %% 3.1 每个月内部，工作日与周末的收入分布和波动有何不同？
# 三个月使用同一纵轴尺度，便于比较；须线外的数据点照常显示，不删除。
fig, axes = plt.subplots(1, 3, figsize=(12, 4), sharey=True, layout="constrained")
fig.suptitle("Monthly Revenue Distributions: Weekdays vs Weekends")

for ax, month in zip(axes, months):
    month_data = data.loc[data["month"].eq(month)]
    groups = [
        month_data.loc[month_data["day_type"].eq(g), "revenue"]
        for g in day_order
    ]
    boxes = ax.boxplot(
        groups,
        positions=[1, 2],
        widths=0.5,
        patch_artist=True,
        showfliers=True,
        medianprops={"color": "black", "linewidth": 1.5}
    )
    for box, color in zip(boxes["boxes"], ["#2563A6", "#DE8F32"]):
        box.set_facecolor(color)
        box.set_alpha(0.35)
    ax.set_xticks([1, 2], day_order)
    ax.set_title(month)
    ax.grid(axis="y", alpha=0.25)

axes[0].set_ylabel("Revenue (CNY)")
fig.savefig(FIGURES_DIR / "04_monthly_boxplots.png", dpi=160, bbox_inches="tight")

# %% 4. 合并 7—8 月作为基准，9 月两组日均收入变化了多少？
print("\n—— 4. 7—8 月与 9 月比较 ——")
# 合并每日记录求均值，不简单平均两个“月均值”
baseline = (
    data.loc[data["month"].isin(["2026-07", "2026-08"])]
    .groupby("day_type")["revenue"]
    .agg(days="count", mean="mean")
    .reindex(day_order)
)

september = (
    data.loc[data["month"].eq("2026-09")]
    .groupby("day_type")["revenue"]
    .agg(days="count", mean="mean")
    .reindex(day_order)
)

comparison = pd.DataFrame({
    "Jul-Aug_days": baseline["days"],
    "Sep_days": september["days"],
    "Jul-Aug_mean_CNY": baseline["mean"],
    "Sep_mean_CNY": september["mean"]
})

comparison["change_CNY"] = (
    comparison["Sep_mean_CNY"] - comparison["Jul-Aug_mean_CNY"]
)

# 基准为零时百分比无定义，保留 NaN，避免除以零
comparison["change_pct"] = (
    comparison["change_CNY"]
    / comparison["Jul-Aug_mean_CNY"].replace(0, float("nan"))
    * 100
)

print(
    comparison.rename(
        index=day_names,
        columns={
            "Jul-Aug_days": "7—8月天数",
            "Sep_days": "9月天数",
            "Jul-Aug_mean_CNY": "7—8月日均(CNY)",
            "Sep_mean_CNY": "9月日均(CNY)",
            "change_CNY": "日均变化(CNY)",
            "change_pct": "日均变化(%)"
        }
    ).round(2).to_string()
)

# 根据实际计算值输出说明，不预写增长或下降结论
for g in day_order:
    row = comparison.loc[g]
    print(
        f"{day_names[g]}："
        f"日均由 {row['Jul-Aug_mean_CNY']:.2f} CNY "
        f"变为 {row['Sep_mean_CNY']:.2f} CNY，"
        f"变化 {row['change_CNY']:+.2f} CNY"
        f"（{row['change_pct']:+.2f}%）。"
    )

gap = (
    comparison.loc["Weekday", "change_CNY"]
    - comparison.loc["Weekend", "change_CNY"]
)

if gap > 0:
    print(f"工作日的日均变化金额比周末高 {gap:.2f} CNY。")
elif gap < 0:
    print(f"周末的日均变化金额比工作日高 {-gap:.2f} CNY。")
else:
    print("两组的日均变化金额相同。")

# %% 保存描述性统计表，并继续执行回测（此处不暂停显示图表）。
summary.to_csv(RESULTS_DIR / "monthly_summary.csv", encoding="utf-8-sig")
overall.to_csv(RESULTS_DIR / "overall_day_type_stats.csv", encoding="utf-8-sig")
monthly_stats.to_csv(RESULTS_DIR / "monthly_day_type_stats.csv", encoding="utf-8-sig")
comparison.to_csv(RESULTS_DIR / "september_vs_july_august.csv", encoding="utf-8-sig")
print("这些统计描述收入差异；上班、上学及开学带动需求仍是待检验解释。")

# %% 每日收入预测回测：先预测，再更新当天的真实记录。
from math import isfinite


def backtest_daily_revenue(source_df):
    """以 2026 年 9 月营业日为测试集，逐日预测后再更新历史。"""
    # 1. 检查并复制数据。按日期排序，日期和金额均不改写。
    columns = ["date", "revenue", "month", "weekday", "is_weekend"]
    missing_columns = set(columns).difference(source_df.columns)
    if missing_columns:
        raise ValueError(f"df 缺少列：{sorted(missing_columns)}")
    records = source_df[columns].copy(deep=True).sort_values("date").reset_index(drop=True)
    if records[columns].isna().any().any():
        raise ValueError("输入数据有缺失值，请核查；回测不会补造数据。")
    if not pd.api.types.is_datetime64_any_dtype(records["date"]):
        raise TypeError("date 必须已经是 datetime 类型。")
    if not records["date"].eq(records["date"].dt.normalize()).all():
        raise ValueError("date 应为每日日期，不应包含具体时刻。")
    if records["date"].duplicated().any():
        raise ValueError("存在重复日期，请先核查。")
    if not pd.api.types.is_numeric_dtype(records["revenue"]):
        raise TypeError("revenue 必须为数值类型。")
    if not records["revenue"].map(isfinite).all():
        raise ValueError("收入包含无穷值，请先核查。")
    if not records["month"].eq(records["date"].dt.strftime("%Y-%m")).all():
        raise ValueError("month 与 date 不一致。")
    if not records["weekday"].eq(records["date"].dt.dayofweek).all():
        raise ValueError("weekday 与 date 不一致。")
    if not records["is_weekend"].eq(records["weekday"].ge(5)).all():
        raise ValueError("is_weekend 与 weekday 不一致。")

    # 只测试 df 中真实存在的 9 月营业日；不补停业日期。
    test_rows = records.loc[records["month"].eq("2026-09")]
    if test_rows.empty:
        raise ValueError("df 中没有 2026 年 9 月的营业日记录。")
    history = records.loc[records["date"].lt(test_rows["date"].min())].copy()
    required_counts = {"A": 7, "B": 4, "C": 4}
    results = []

    # 2. 按日期向前推进：先预测，再读取当日实际收入，最后更新历史。
    for row_index in test_rows.index:
        target_date = test_rows.at[row_index, "date"]
        target_weekday = target_date.dayofweek
        target_weekend = target_weekday >= 5
        assert history["date"].lt(target_date).all(), "历史记录包含预测日或未来日期。"

        # “最近”按日期排序；营业日指有真实记录的日期，并非日历天数。
        samples = {
            "A": history.tail(7),
            "B": history.loc[history["weekday"].eq(target_weekday)].tail(4),
            "C": history.loc[history["is_weekend"].eq(target_weekend)].tail(4),
        }
        output = {
            "date": target_date,
            "day_type": "Weekend" if target_weekend else "Weekday",
        }
        for method, sample in samples.items():
            # 每次预测都检查：任何选取日期必须严格早于预测日期。
            assert sample["date"].lt(target_date).all(), f"{method} 方法存在未来数据泄漏。"
            assert sample["date"].is_unique, f"{method} 方法样本包含重复日期。"
            n = len(sample)
            required = required_counts[method]
            output[f"{method}_history_n"] = n
            # 样本不足时这些日期仅代表可用候选记录，并未生成预测。
            output[f"{method}_history_dates"] = "|".join(sample["date"].dt.strftime("%Y-%m-%d"))
            if n < required:
                output[f"{method}_pred_CNY"] = float("nan")
                output[f"{method}_status"] = f"insufficient_history:{n}/{required}"
            else:
                output[f"{method}_pred_CNY"] = float(sample["revenue"].mean())
                output[f"{method}_status"] = "ok"

        # 三种预测完成后，才读取当天实际记录值，并将当天加入历史。
        completed_day = test_rows.loc[[row_index]]
        output["actual_recorded_CNY"] = float(completed_day.iloc[0]["revenue"])
        results.append(output)
        history = pd.concat([history, completed_day], ignore_index=True)

    # 3. 所有方法均有预测的相同日期才进入 MAE 比较。
    predictions = pd.DataFrame(results)
    pred_columns = [f"{method}_pred_CNY" for method in required_counts]
    predictions["in_common_evaluation"] = predictions[pred_columns].notna().all(axis=1)
    for method in required_counts:
        predictions[f"{method}_absolute_error_CNY"] = (
            predictions[f"{method}_pred_CNY"] - predictions["actual_recorded_CNY"]
        ).abs()
    common = predictions.loc[predictions["in_common_evaluation"]]
    metric_rows = []
    for method in required_counts:
        metric = {"method": method}
        for group, mask in {
            "overall": pd.Series(True, index=common.index),
            "weekday": common["day_type"].eq("Weekday"),
            "weekend": common["day_type"].eq("Weekend"),
        }.items():
            errors = common.loc[mask, f"{method}_absolute_error_CNY"]
            metric[f"{group}_days"] = len(errors)
            # 没有可评估记录时，均值为 NaN，不记成零误差。
            metric[f"{group}_MAE_CNY"] = errors.mean()
        metric_rows.append(metric)
    metrics = pd.DataFrame(metric_rows).set_index("method")

    # CSV 中优先排列实际值、预测值、共同评估标记，其余为审计信息。
    first_columns = ["date", "day_type", "actual_recorded_CNY", *pred_columns, "in_common_evaluation"]
    remaining_columns = [column for column in predictions if column not in first_columns]
    return predictions[first_columns + remaining_columns], metrics


# %% 执行回测并打印结果
bt_predictions, bt_metrics = backtest_daily_revenue(df)
print("\n—— 每日收入预测回测：2026 年 9 月 ——")
print("口径：实际记录值含估算现金，未含支付宝；预测值和 MAE 单位均为人民币元。")
print("A：最近 7 个营业日均值；B：最近 4 个相同星期几营业日均值；C：最近 4 个相同日类型营业日均值。")
print("工作日按周一至周五分类，周末按周六、周日分类，未按节假日或调休调整。")
bt_print_columns = ["date", "actual_recorded_CNY", "A_pred_CNY", "B_pred_CNY", "C_pred_CNY"]
print(bt_predictions[bt_print_columns].rename(columns={
    "date": "预测日期", "actual_recorded_CNY": "实际记录值(元)",
    "A_pred_CNY": "A预测(元)", "B_pred_CNY": "B预测(元)", "C_pred_CNY": "C预测(元)"
}).to_string(index=False, float_format=lambda value: f"{value:.2f}", na_rep="历史不足"))

bt_common_count = int(bt_predictions["in_common_evaluation"].sum())
print(f"\n测试日期 {len(bt_predictions)} 天；三种方法共同可评估 {bt_common_count} 天。")
for bt_method in ["A", "B", "C"]:
    bt_missing = bt_predictions.loc[bt_predictions[f"{bt_method}_pred_CNY"].isna()]
    print(f"方法 {bt_method} 历史不足：{len(bt_missing)} 天。")
    if not bt_missing.empty:
        print(bt_missing[["date", f"{bt_method}_status"]].to_string(index=False))
print("\nMAE = 共同评估日期上 |预测值 − 实际记录值| 的平均值：")
print(bt_metrics.rename(columns={
    "overall_days": "整体天数", "overall_MAE_CNY": "整体MAE(元)",
    "weekday_days": "工作日天数", "weekday_MAE_CNY": "工作日MAE(元)",
    "weekend_days": "周末天数", "weekend_MAE_CNY": "周末MAE(元)",
}).to_string(float_format=lambda value: f"{value:.2f}", na_rep="无可评估日期"))
print("所有预测所选日期均通过严格早于预测日期的检查。")
print("MAE 越小表示本次测试样本上的绝对误差越小；本轮结果不能保证未来表现。")


# %% 保存逐日结果，并新增一张整体 MAE 柱状图
# CSV 保存到 results，全部五张图保存到 figures。
bt_output_dir = RESULTS_DIR
bt_figures_dir = FIGURES_DIR
bt_figures_dir.mkdir(parents=True, exist_ok=True)
bt_csv_path = bt_output_dir / "daily_revenue_backtest_predictions.csv"
bt_metrics_path = bt_output_dir / "daily_revenue_backtest_mae.csv"
bt_figure_path = bt_figures_dir / "05_backtest_mae.png"

# 保存未四舍五入的计算值。utf-8-sig 便于 Excel 识别中文。
bt_predictions.to_csv(bt_csv_path, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
bt_metrics.to_csv(bt_metrics_path, encoding="utf-8-sig")

bt_fig, bt_ax = plt.subplots(figsize=(8, 4.5), layout="constrained")
if bt_common_count:
    bt_bars = bt_ax.bar(
        ["A\nLast 7 open days", "B\nLast 4 same weekdays", "C\nLast 4 same day types"],
        bt_metrics.loc[["A", "B", "C"], "overall_MAE_CNY"],
        color=["#2563A6", "#DE8F32", "#359A70"], width=0.6
    )
    bt_ax.bar_label(bt_bars, fmt="%.2f", padding=4)
    bt_ax.set_ylim(0, max(1.0, bt_metrics["overall_MAE_CNY"].max() * 1.2))
else:
    bt_ax.text(0.5, 0.5, "No common evaluation dates", ha="center", va="center", transform=bt_ax.transAxes)
bt_ax.set(
    title=f"September 2026 Backtest: Overall MAE (n={bt_common_count})",
    xlabel="Forecast method", ylabel="MAE (CNY)"
)
bt_ax.grid(axis="y", alpha=0.25)
bt_fig.savefig(bt_figure_path, dpi=160, bbox_inches="tight")

print(f"\n逐日预测 CSV：{bt_csv_path}")
print(f"MAE 汇总 CSV：{bt_metrics_path}")
print(f"MAE 柱状图：{bt_figure_path}")
# 全部计算完成后统一显示，避免前四张图阻塞回测。
print(f"全部五张图片已保存到：{FIGURES_DIR}")
if args.no_show:
    plt.close("all")
else:
    plt.show()
