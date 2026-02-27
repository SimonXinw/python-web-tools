import json
import os
import sys
import time
from datetime import datetime

import akshare as ak
import baostock as bs
import requests

SYMBOL = "515180"
ETF_NAME = "易方达中证红利ETF"
MA250_N = 250
START_DATE = "20100101"
END_DATE = datetime.now().strftime("%Y%m%d")

SUPABASE_URL = "https://lvsyycnybkwbrvvmshfb.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imx2c3l5Y255Ymt3YnJ2dm1zaGZiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTcyNTU5NjMsImV4cCI6MjA3MjgzMTk2M30.Ot7-h6nbAhIkUOGoqAv8diUBW6-Llhh8MtA6bJMXbeA"
SUPABASE_TABLE = "yfd_dividend"
BATCH_SIZE = 500


# ── MA250 计算 ────────────────────────────────────────────────────────────────

def calc_ma(data, n):
    result = []
    for i in range(len(data)):
        if i < n - 1:
            result.append(None)
        else:
            avg = sum(data[i - n + 1 : i + 1]) / n
            result.append(round(avg, 4))
    return result


# ── 统一格式化：把任意来源的 (dates, closes, change_pcts, source) 转为标准记录 ──

def normalize(dates, closes, change_pcts, source):
    ma250_list = calc_ma(closes, MA250_N)
    records = []
    for date, close, change_pct, ma in zip(dates, closes, change_pcts, ma250_list):
        dev_pct = round((close / ma - 1) * 100, 4) if ma is not None else None
        records.append(
            {
                "date": date,
                "source": source,
                "net_price": close,
                "net_totsl": None,
                "net_scale": change_pct,
                "adj_net_price": close,
                "ma250": ma,
                "nav_ma250_deviation": dev_pct,
            }
        )
    return records


# ── 数据源 1：东方财富 基金接口（akshare fund_etf_hist_em）────────────────────

def fetch_from_em_fund():
    print("  [数据源1] 东方财富基金接口 fund_etf_hist_em ...")
    df = ak.fund_etf_hist_em(
        symbol=SYMBOL,
        period="daily",
        start_date=START_DATE,
        end_date=END_DATE,
        adjust="qfq",
    )
    df = df.sort_values("日期").reset_index(drop=True)
    dates = df["日期"].astype(str).tolist()
    closes = [round(float(v), 4) for v in df["收盘"].tolist()]
    change_pcts = [round(float(v), 4) for v in df["涨跌幅"].tolist()]
    return normalize(dates, closes, change_pcts, "akshare/东方财富基金")


# ── 数据源 2：东方财富 股票接口（akshare stock_zh_a_hist）────────────────────
# 注意：与数据源1同属东方财富服务器，IP 被限速时两者同时失败，非真正冗余

def fetch_from_em_stock():
    print("  [数据源2] 东方财富股票接口 stock_zh_a_hist ...")
    df = ak.stock_zh_a_hist(
        symbol=SYMBOL,
        period="daily",
        start_date=START_DATE,
        end_date=END_DATE,
        adjust="qfq",
    )
    df = df.sort_values("日期").reset_index(drop=True)
    dates = df["日期"].astype(str).tolist()
    closes = [round(float(v), 4) for v in df["收盘"].tolist()]
    change_pcts = [round(float(v), 4) for v in df["涨跌幅"].tolist()]
    return normalize(dates, closes, change_pcts, "akshare/东方财富股票")


# ── 数据源 3：新浪财经（fund_etf_hist_sina，独立服务器，东方财富限速时有效）──

def fetch_from_sina():
    print("  [数据源3] 新浪财经 fund_etf_hist_sina ...")
    df = ak.fund_etf_hist_sina(symbol=f"sh{SYMBOL}")
    df = df.sort_values("date").reset_index(drop=True)

    dates = df["date"].astype(str).tolist()
    closes = [round(float(v), 4) for v in df["close"].tolist()]

    # 新浪接口无涨跌幅列，通过相邻收盘价计算
    change_pcts = [0.0]
    for i in range(1, len(closes)):
        pct = round((closes[i] - closes[i - 1]) / closes[i - 1] * 100, 4)
        change_pcts.append(pct)

    return normalize(dates, closes, change_pcts, "akshare/新浪财经")


# ── 数据源 4：baostock（完全独立，不依赖东方财富）────────────────────────────

def fetch_from_baostock():
    print("  [数据源3] baostock ...")
    lg = bs.login()
    if lg.error_code != "0":
        raise RuntimeError(f"baostock 登录失败: {lg.error_msg}")

    rs = bs.query_history_k_data_plus(
        f"sh.{SYMBOL}",
        "date,close,pctChg",
        start_date=START_DATE[:4] + "-" + START_DATE[4:6] + "-" + START_DATE[6:],
        end_date=END_DATE[:4] + "-" + END_DATE[4:6] + "-" + END_DATE[6:],
        frequency="d",
        adjustflag="2",  # 前复权
    )
    rows = []
    while rs.error_code == "0" and rs.next():
        rows.append(rs.get_row_data())
    bs.logout()

    if not rows:
        raise RuntimeError("baostock 返回数据为空")

    rows.sort(key=lambda r: r[0])
    dates = [r[0] for r in rows]
    closes = [round(float(r[1]), 4) for r in rows]
    change_pcts = [round(float(r[2]), 4) for r in rows]
    return normalize(dates, closes, change_pcts, "baostock")


# ── 按顺序尝试所有数据源，第一个成功的直接返回 ────────────────────────────────

def fetch_and_build():
    sources = [fetch_from_em_fund, fetch_from_em_stock, fetch_from_sina, fetch_from_baostock]
    last_err = None

    for fetch_fn in sources:
        try:
            records = fetch_fn()
            print(f"  成功，共 {len(records)} 条记录，来源：{records[0]['source']}")
            return records
        except Exception as e:
            print(f"  失败：{e}")
            last_err = e

    raise RuntimeError(f"所有数据源均失败，最后一个错误：{last_err}")


# ── Supabase ──────────────────────────────────────────────────────────────────

def supabase_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }


def supabase_delete_all():
    print(f"正在删除 {SUPABASE_TABLE} 表全部数据...")
    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}?date=not.is.null"
    resp = requests.delete(url, headers=supabase_headers(), timeout=30)
    if resp.status_code not in (200, 204):
        raise RuntimeError(f"删除失败: HTTP {resp.status_code} — {resp.text}")
    print("删除完成")


def supabase_insert_all(records):
    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}"
    total = len(records)
    inserted = 0

    for i in range(0, total, BATCH_SIZE):
        batch = records[i : i + BATCH_SIZE]
        clean_batch = [
            {k: v for k, v in r.items() if v is not None}
            for r in batch
        ]
        resp = requests.post(url, headers=supabase_headers(), json=clean_batch, timeout=30)
        if resp.status_code not in (200, 201):
            raise RuntimeError(
                f"插入失败 batch {i // BATCH_SIZE + 1}: HTTP {resp.status_code} — {resp.text}"
            )
        inserted += len(batch)
        print(f"已插入: {inserted}/{total}")
        time.sleep(0.1)

    return inserted


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "etf_515180_data.json")

    sync_only = "--sync-only" in sys.argv

    if sync_only:
        if not os.path.exists(output_path):
            print("错误：JSON 文件不存在，请先不带 --sync-only 运行一次")
            sys.exit(1)
        print(f"[sync-only] 读取已有 JSON: {output_path}")
        with open(output_path, encoding="utf-8") as f:
            data = json.load(f)
        records = data["records"]
        print(f"已读取 {len(records)} 条，生成于 {data['generated_at']}")
    else:
        print(f"正在拉取 {SYMBOL} ({ETF_NAME}) 前复权历史数据...")
        records = fetch_and_build()

        output = {
            "symbol": SYMBOL,
            "name": ETF_NAME,
            "generated_at": datetime.now().strftime("%Y-%m-%d"),
            "records": records,
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        last = records[-1]
        print(f"JSON 已生成: {output_path}")
        print(f"总记录数          : {len(records)}")
        print(f"最新日期          : {last['date']}")
        print(f"adj_net_price     : {last['adj_net_price']}")
        print(f"net_scale (涨跌幅): {last['net_scale']}%")
        print(f"ma250             : {last['ma250']}")
        print(f"偏离度            : {last['nav_ma250_deviation']}%")

    print("\n开始同步到 Supabase...")
    supabase_delete_all()
    inserted = supabase_insert_all(records)
    print(f"\n同步完成！共插入 {inserted} 条记录到 {SUPABASE_TABLE}")


if __name__ == "__main__":
    main()
