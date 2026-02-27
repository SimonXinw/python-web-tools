import json
import os
import sys
import time
from datetime import datetime

import akshare as ak
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


def calc_ma(data, n):
    result = []
    for i in range(len(data)):
        if i < n - 1:
            result.append(None)
        else:
            avg = sum(data[i - n + 1 : i + 1]) / n
            result.append(round(avg, 4))
    return result


def fetch_and_build():
    print(f"正在拉取 {SYMBOL} ({ETF_NAME}) 前复权历史数据...")

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
    ma250_list = calc_ma(closes, MA250_N)

    records = []
    for date, close, change_pct, ma in zip(dates, closes, change_pcts, ma250_list):
        dev_pct = None
        if ma is not None:
            dev_pct = round((close / ma - 1) * 100, 4)

        records.append(
            {
                "date": date,
                "source": "akshare",
                "net_price": close,
                "net_totsl": None,
                "net_scale": change_pct,
                "adj_net_price": close,
                "ma250": ma,
                "nav_ma250_deviation": dev_pct,
            }
        )

    return records


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
