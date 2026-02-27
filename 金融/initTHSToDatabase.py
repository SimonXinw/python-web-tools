import csv
import io
import json
import os
import time
from datetime import datetime

import requests

SYMBOL = "515180"
ETF_NAME = "易方达中证红利ETF"
MA250_N = 250
SOURCE = "同花顺/THS"

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


# ── 格式化：THS 数据转为标准记录 ──────────────────────────────────────────────

def normalize(dates, closes, change_pcts):
    ma250_list = calc_ma(closes, MA250_N)
    records = []
    for date, close, change_pct, ma in zip(dates, closes, change_pcts, ma250_list):
        dev_pct = round((close / ma - 1) * 100, 4) if ma is not None else None
        records.append(
            {
                "date": date,
                "source": SOURCE,
                "net_price": close,
                "net_totsl": None,
                "net_scale": change_pct,
                "adj_net_price": close,
                "ma250": ma,
                "nav_ma250_deviation_pct": dev_pct,
            }
        )
    return records


# ── 解析涨幅字段：支持 "--"、"-1.50%"、纯数字 ────────────────────────────────

def parse_change_pct(value):
    s = str(value).strip()
    if s in ("--", "-", "", "null"):
        return 0.0
    s = s.replace("%", "")
    try:
        return round(float(s), 4)
    except ValueError:
        return 0.0


# ── 解析日期：把 "2019-12-20,五" → "2019-12-20" ───────────────────────────────

def parse_date(value):
    return str(value).strip().split(",")[0].strip()


# ── 读取同花顺 XLS（实为 GBK Tab 分隔文本）───────────────────────────────────

def load_xls(xls_path):
    print(f"正在读取文件: {xls_path}")

    with open(xls_path, "rb") as f:
        raw = f.read()
    text = raw.decode("gbk", errors="replace")

    reader = csv.reader(io.StringIO(text), delimiter="\t")
    rows = list(reader)

    header = [col.strip() for col in rows[0]]
    print(f"表头: {header}")

    # 列索引映射
    col_map = {name: idx for idx, name in enumerate(header)}
    date_col = col_map.get("时间")
    close_col = col_map.get("收盘")
    change_col = col_map.get("涨幅")

    if date_col is None or close_col is None:
        raise RuntimeError(f"未找到必须列（时间/收盘），当前表头: {header}")

    dates, closes, change_pcts = [], [], []

    for row_idx, row in enumerate(rows[1:], start=2):
        if len(row) <= max(date_col, close_col):
            continue

        raw_date = row[date_col].strip()
        raw_close = row[close_col].strip()
        raw_change = row[change_col].strip() if change_col is not None and len(row) > change_col else "--"

        date_str = parse_date(raw_date)
        if not date_str:
            continue

        try:
            close_val = round(float(raw_close), 4)
        except (ValueError, TypeError):
            print(f"  跳过第 {row_idx} 行，收盘价无效: {raw_close!r}")
            continue

        dates.append(date_str)
        closes.append(close_val)
        change_pcts.append(parse_change_pct(raw_change))

    # THS 导出通常是降序，按日期升序排列
    combined = sorted(zip(dates, closes, change_pcts), key=lambda x: x[0])
    dates, closes, change_pcts = zip(*combined)

    print(f"共读取 {len(dates)} 条有效记录，日期范围: {dates[0]} ~ {dates[-1]}")
    return list(dates), list(closes), list(change_pcts)


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
        resp = requests.post(url, headers=supabase_headers(), json=batch, timeout=30)
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
    xls_path = os.path.join(script_dir, "tonghuashun_data.xls")
    json_path = os.path.join(script_dir, "etf_515180_data.json")

    if not os.path.exists(xls_path):
        raise FileNotFoundError(f"找不到文件: {xls_path}")

    dates, closes, change_pcts = load_xls(xls_path)
    records = normalize(dates, closes, change_pcts)

    last = records[-1]
    print(f"\n数据预览（最新一条）:")
    print(f"  日期              : {last['date']}")
    print(f"  收盘价            : {last['net_price']}")
    print(f"  涨幅              : {last['net_scale']}%")
    print(f"  ma250             : {last['ma250']}")
    print(f"  偏离度            : {last['nav_ma250_deviation_pct']}%")

    # ── 保存 JSON（供红利策略.html 直接读取）─────────────────────────────────
    output = {
        "symbol": SYMBOL,
        "name": ETF_NAME,
        "generated_at": datetime.now().strftime("%Y-%m-%d"),
        "records": records,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\nJSON 已保存: {json_path}（共 {len(records)} 条）")

    # ── 同步到 Supabase ───────────────────────────────────────────────────────
    print("\n开始同步到 Supabase...")
    supabase_delete_all()
    inserted = supabase_insert_all(records)
    print(f"\n同步完成！共插入 {inserted} 条记录到 {SUPABASE_TABLE}")


if __name__ == "__main__":
    main()
