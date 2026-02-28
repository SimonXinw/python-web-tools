"""
易方达中证红利ETF (515180) · 策略回测
数据来源：etf_515180_data.json / tonghuashun_data.xls（前复权价格）

回测策略：
  A) 买入持有     — 首日一次性满仓，永久持有
  B) 周定投(周二) — 每周二定投固定金额（按总预算平摊）
  F) 智能策略     — 底仓25% + 智能定投60% + 波段15%（HTML 标准档位）
"""

import os
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")

# ── 参数 ─────────────────────────────────────────────────────────────────────

MA_N = 250
INIT_CAPITAL = 100_000
WEEKLY_BASE = 1_000  # E 策略每周基准定投额

# 定投金额统一规则：总预算相同，按频次平摊
DCA_BUDGET = INIT_CAPITAL  # 定投策略(B/C/D)的总预算

# ── 档位定义 ─────────────────────────────────────────────────────────────────

# F 策略（HTML 标准档位）
ZONES_F = [
    ("极端低估", lambda d: d <= -8, 3.0),
    ("低估加仓", lambda d: -8 < d <= -5, 2.0),
    ("中枢均衡", lambda d: -5 < d < 8, 1.0),
    ("高估减仓", lambda d: 8 <= d < 18, 0.5),
    ("极端高估", lambda d: d >= 18, 0.2),
]


def get_zone(dev, zones):
    for name, cond, factor in zones:
        if cond(dev):
            return name, factor
    return "中枢均衡", 1.0


# ── 加载 & 处理数据 ───────────────────────────────────────────────────────────


def load_data_json(path):
    import json

    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    rows = []
    for r in data["records"]:
        close = r.get("adj_net_price") or r.get("net_price")
        if close is None:
            continue
        rows.append(
            {
                "date": pd.to_datetime(r["date"]),
                "close": float(close),
                "ma250": r.get("ma250"),
                "dev": r.get("nav_ma250_deviation_pct") or r.get("nav_ma250_deviation"),
            }
        )
    df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    if df["ma250"].isna().all():
        df["ma250"] = df["close"].rolling(MA_N).mean().round(6)
        df["dev"] = ((df["close"] / df["ma250"] - 1) * 100).round(4)
    return df


def load_data_xls(path):
    df = pd.read_csv(path, sep="\t", encoding="gbk", header=0)
    df.columns = [
        "date_raw",
        "open",
        "high",
        "low",
        "close",
        "chg_pct",
        "amplitude",
        "volume",
        "amount",
        "turnover",
        "mktcap",
    ][: len(df.columns)]
    df["date"] = pd.to_datetime(df["date_raw"].str.split(",").str[0].str.strip())
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna(subset=["close"]).sort_values("date").reset_index(drop=True)
    df["ma250"] = df["close"].rolling(MA_N).mean().round(6)
    df["dev"] = ((df["close"] / df["ma250"] - 1) * 100).round(4)
    return df


def load_data(script_dir):
    json_path = os.path.join(script_dir, "etf_515180_data.json")
    xls_path = os.path.join(script_dir, "tonghuashun_data.xls")
    if os.path.exists(json_path):
        print(f"  数据源: etf_515180_data.json")
        return load_data_json(json_path)
    elif os.path.exists(xls_path):
        print(f"  数据源: tonghuashun_data.xls")
        return load_data_xls(xls_path)
    raise FileNotFoundError("未找到 etf_515180_data.json 或 tonghuashun_data.xls")


def to_weekly(df):
    return df.groupby(df["date"].dt.to_period("W")).last().reset_index(drop=True)


# ── 通用定投引擎 ──────────────────────────────────────────────────────────────


def run_periodic_dca(daily, period_amt, pick_fn):
    """
    pick_fn(date) → True 表示这天是定投日
    period_amt    → 每次定投金额
    从数据第一天开始（2019-12-20）
    """
    df = daily.copy().reset_index(drop=True)

    shares, invested = 0.0, 0.0
    curve = []

    for _, row in df.iterrows():
        if pick_fn(row["date"]):
            shares += period_amt / row["close"]
            invested += period_amt

        if shares > 0:
            curve.append({"date": row["date"], "value": shares * row["close"]})

    if not curve:
        return None

    curve_df = pd.DataFrame(curve)
    return {
        "total_invested": invested,
        "final_value": shares * df.iloc[-1]["close"],
        "start_date": curve_df.iloc[0]["date"],
        "end_date": df.iloc[-1]["date"],
        "curve": curve_df,
    }


# ── 策略 A：买入持有 ──────────────────────────────────────────────────────────


def run_buy_hold(daily):
    df = daily.reset_index(drop=True)
    p0 = df.iloc[0]["close"]
    shares = INIT_CAPITAL / p0
    curve = [
        {"date": r["date"], "value": shares * r["close"]} for _, r in df.iterrows()
    ]
    return {
        "total_invested": INIT_CAPITAL,
        "final_value": shares * df.iloc[-1]["close"],
        "start_date": df.iloc[0]["date"],
        "end_date": df.iloc[-1]["date"],
        "curve": pd.DataFrame(curve),
    }


# ── 策略 B：周定投（周二）────────────────────────────────────────────────────


def run_weekly_dca(daily):
    df = daily.reset_index(drop=True)
    total_weeks = (df.iloc[-1]["date"] - df.iloc[0]["date"]).days / 7
    per_week = round(DCA_BUDGET / max(total_weeks, 1), 2)

    seen_weeks = set()

    def is_tuesday_or_first(date):
        week_key = date.isocalendar()[:2]
        if week_key in seen_weeks:
            return False
        if date.weekday() <= 1:  # 周一=0, 周二=1
            seen_weeks.add(week_key)
            return True
        seen_weeks.add(week_key)  # 若周一/二非交易日，该周首个交易日也算
        return True

    return run_periodic_dca(daily, per_week, is_tuesday_or_first), per_week


# ── 策略 E / F：智能策略（底仓25% + 智能定投60% + 波段15%）─────────────────


def run_smart_strategy(weekly, zones=None):
    if zones is None:
        zones = ZONES_E

    wv = weekly.reset_index(drop=True)

    base_ratio = 0.25
    dca_ratio = 0.60
    wave_ratio = 0.15

    dca_pool = INIT_CAPITAL * dca_ratio
    wave_pool = INIT_CAPITAL * wave_ratio
    base_cash = INIT_CAPITAL * base_ratio

    base_shares = 0.0
    dca_shares = 0.0
    wave_shares = 0.0
    wave_zone = None
    wave_last_buy_price = None
    wave_add_count = 0

    prev_zone = None
    invested = 0.0
    curve, trades = [], []

    def pv(price):
        return (
            (base_shares + dca_shares + wave_shares) * price
            + dca_pool
            + wave_pool
            + base_cash
        )

    for _, row in wv.iterrows():
        price = row["close"]
        ma250_val = row["ma250"]
        date = row["date"]

        # MA250 未就绪时默认 0% 偏离（中枢均衡 ×1）
        if ma250_val is None or pd.isna(ma250_val) or ma250_val == 0:
            dev = 0.0
        else:
            dev = (price / ma250_val - 1) * 100
        zone, factor = get_zone(dev, zones)
        entering = zone != prev_zone

        if base_shares == 0 and base_cash > 0:
            base_shares = base_cash / price
            invested += base_cash
            base_cash = 0.0
            trades.append(("底仓建仓", date, price, INIT_CAPITAL * base_ratio))

        dca_amt = min(WEEKLY_BASE * factor, dca_pool)
        if dca_amt > 0:
            dca_shares += dca_amt / price
            dca_pool -= dca_amt
            invested += dca_amt

        if wave_shares > 0:
            sell_frac = 0.0
            if wave_zone == "极端低估":
                if dev >= 5:
                    sell_frac = 1.0
                elif dev >= 0:
                    sell_frac = 0.5
                elif dev >= -5:
                    sell_frac = 0.3
            elif wave_zone == "低估加仓":
                if dev >= 3:
                    sell_frac = 1.0
                elif dev >= 0:
                    sell_frac = 0.5
            if zone in ("高估减仓", "极端高估") and entering:
                sell_frac = 1.0
            if sell_frac > 0:
                sell = wave_shares * sell_frac
                recv = sell * price
                old_zone = wave_zone
                wave_pool += recv
                wave_shares -= sell
                trades.append(
                    (f"波段卖出{int(sell_frac*100)}%({old_zone})", date, price, recv)
                )
                if wave_shares < 1e-9:
                    wave_shares = 0.0
                    wave_zone = None
                    wave_last_buy_price = None
                    wave_add_count = 0

        if zone in ("极端低估", "低估加仓") and wave_pool > 0:
            max_adds = 2 if zone == "极端低估" else 3
            drop_thres = 0.02 if zone == "极端低估" else 0.01
            unit_amt = WEEKLY_BASE * 10 if zone == "极端低估" else WEEKLY_BASE * 5

            if wave_shares == 0 and entering:
                wave_amt = min(unit_amt, wave_pool)
                if wave_amt > 0:
                    wave_shares += wave_amt / price
                    wave_pool -= wave_amt
                    wave_zone = zone
                    wave_last_buy_price = price
                    wave_add_count = 0
                    invested += wave_amt
                    trades.append((f"波段建仓({zone})", date, price, wave_amt))
            elif (
                wave_shares > 0
                and wave_zone == zone
                and wave_last_buy_price is not None
            ):
                if wave_add_count < max_adds and price <= wave_last_buy_price * (
                    1 - drop_thres
                ):
                    add_amt = min(unit_amt, wave_pool)
                    if add_amt > 0:
                        wave_shares += add_amt / price
                        wave_pool -= add_amt
                        wave_last_buy_price = price
                        wave_add_count += 1
                        invested += add_amt
                        trades.append(
                            (f"波段追加{wave_add_count}({zone})", date, price, add_amt)
                        )

        curve.append({"date": date, "value": pv(price)})
        prev_zone = zone

    final_value = pv(wv.iloc[-1]["close"])
    return {
        "total_invested": invested,
        "final_value": final_value,
        "start_date": wv.iloc[0]["date"],
        "end_date": wv.iloc[-1]["date"],
        "curve": pd.DataFrame(curve),
        "trades": pd.DataFrame(trades, columns=["type", "date", "price", "amount"]),
    }


# ── 绩效计算 ──────────────────────────────────────────────────────────────────


def calc_metrics(res):
    iv = res["total_invested"]
    fv = res["final_value"]
    years = (res["end_date"] - res["start_date"]).days / 365.25

    profit = fv - iv
    ret_pct = profit / iv * 100
    cagr = ((fv / iv) ** (1 / years) - 1) * 100 if years > 0 else 0

    vals = res["curve"]["value"].values
    peak = np.maximum.accumulate(vals)
    mdd = ((vals - peak) / peak * 100).min()

    return {
        "invested": iv,
        "final": fv,
        "profit": profit,
        "ret_pct": ret_pct,
        "cagr": cagr,
        "mdd": mdd,
        "years": years,
    }


# ── 主函数 ────────────────────────────────────────────────────────────────────


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    print("正在加载数据...")
    daily = load_data(script_dir)
    weekly = to_weekly(daily)

    first_day = daily.iloc[0]
    first_ma  = daily[daily["ma250"].notna()].iloc[0]
    last_day  = daily.iloc[-1]

    print(f"数据范围  : {first_day['date'].date()} → {last_day['date'].date()}  共 {len(daily)} 交易日")
    print(f"起投日期  : {first_day['date'].date()}  首日收盘 {first_day['close']:.4f}")
    print(f"MA250 首日: {first_ma['date'].date()}  (前 249 日 E 策略视为 0% 偏离)")
    print(f"最新收盘  : {last_day['close']:.4f}   偏离年线 {last_day['dev']:+.2f}%")
    print()

    # ── 运行三个策略 ──────────────────────────────────────────────────────────
    res_A = run_buy_hold(daily)
    res_B, b_per = run_weekly_dca(daily)
    res_F = run_smart_strategy(weekly, zones=ZONES_F)

    mA = calc_metrics(res_A)
    mB = calc_metrics(res_B)
    mF = calc_metrics(res_F)

    def r(v):
        return f"{v:>10,.0f}"

    def p(v):
        return f"{v:>9.2f}%"

    # ── 对比表 ────────────────────────────────────────────────────────────────
    sep = "─" * 66
    print(sep)
    print(f"  {'指标':<16}  {'A 买入持有':>10}  {'B 周定投':>10}  {'F 智能策略':>10}")
    print(sep)

    items = [
        ("投入本金（元）", [mA, mB, mF], "invested", r),
        ("最终价值（元）", [mA, mB, mF], "final", r),
        ("净利润（元）",   [mA, mB, mF], "profit", r),
        ("总收益率",       [mA, mB, mF], "ret_pct", p),
        ("年化CAGR",       [mA, mB, mF], "cagr", p),
        ("最大回撤",       [mA, mB, mF], "mdd", p),
        ("回测年限（年）", [mA, mB, mF], "years", lambda v: f"{v:>10.2f}"),
    ]
    for label, ms, key, fmt in items:
        vals = "  ".join(fmt(m[key]) for m in ms)
        print(f"  {label:<16}  {vals}")
    print(sep)

    # ── 定投频率说明 ──────────────────────────────────────────────────────────
    print()
    print("  ── 定投频率 & 每次金额（总预算均为 10 万元）──")
    print(f"  B 周定投(周二):  每周 {b_per:,.0f} 元")

    # ── 各策略平均成本 ────────────────────────────────────────────────────────
    print()
    print("  ── 平均买入成本对比 ──")
    for name, m in [
        ("A 买入持有", mA),
        ("B 周定投", mB),
        ("F 智能策略", mF),
    ]:
        avg = m["invested"] / (m["final"] / last_day["close"])
        print(
            f"  {name:<12}  均价 {avg:.4f}  (当前价/均价 = {last_day['close']/avg:.2f}x)"
        )

    # ── F 策略交易记录 ────────────────────────────────────────────────────────
    trades = res_F["trades"].copy()
    trades["date"] = trades["date"].dt.strftime("%Y-%m-%d")
    trades["price"] = trades["price"].map("{:.4f}".format)
    trades["amount"] = trades["amount"].map("{:,.0f}".format)
    print()
    print(f"  ── 策略 F 交易记录（共 {len(res_F['trades'])} 笔）──")
    print(trades.to_string(index=False))

    print()
    print("回测完成！")


if __name__ == "__main__":
    main()
