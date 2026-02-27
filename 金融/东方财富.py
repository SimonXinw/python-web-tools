import json
import os
from datetime import datetime

import akshare as ak

SYMBOL = "515180"
ETF_NAME = "易方达中证红利ETF"
MA250_N = 250
START_DATE = "20100101"
END_DATE = datetime.now().strftime("%Y%m%d")


def calc_ma(data, n):
    result = []
    for i in range(len(data)):
        if i < n - 1:
            result.append(None)
        else:
            avg = sum(data[i - n + 1 : i + 1]) / n
            result.append(round(avg, 4))
    return result


def main():
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

    ma250_list = calc_ma(closes, MA250_N)

    records = []
    for date, close, ma in zip(dates, closes, ma250_list):
        dev_pct = None
        if ma is not None:
            dev_pct = round((close / ma - 1) * 100, 2)

        records.append(
            {
                "date": date,
                "close": close,
                "ma250": ma,
                "dev_pct": dev_pct,
            }
        )

    output = {
        "symbol": SYMBOL,
        "name": ETF_NAME,
        "generated_at": datetime.now().strftime("%Y-%m-%d"),
        "records": records,
    }

    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "etf_515180_data.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    last = records[-1]
    print(f"数据已生成: {output_path}")
    print(f"总记录数: {len(records)}")
    print(f"最新日期: {last['date']}")
    print(f"最新前复权收盘: {last['close']}")
    print(f"MA250: {last['ma250']}")
    print(f"偏离度: {last['dev_pct']}%")


if __name__ == "__main__":
    main()
