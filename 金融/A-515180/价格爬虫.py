import re
import time
import random
import requests
from bs4 import BeautifulSoup

SYMBOL = "515180"
URL = f"https://www.aastocks.com/tc/cnhk/analysis/company-fundamental/company-information?shsymbol={SYMBOL}"

HEADERS_POOL = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.aastocks.com/tc/cnhk/quote/quick-quote.aspx",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.aastocks.com/tc/cnhk/quote/quick-quote.aspx",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-TW,zh;q=0.8,en-US;q=0.5,en;q=0.3",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.aastocks.com/",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    },
]


def parse_change(change_text):
    """从 '+0.015 (1.042%)' 解析出涨跌额和涨跌幅百分比"""
    match = re.search(r"([+-]?\d+\.?\d*)\s*\(([+-]?\d+\.?\d*)%\)", change_text)
    if match:
        return float(match.group(1)), float(match.group(2))
    return None, None


def fetch_price():
    headers = random.choice(HEADERS_POOL)

    session = requests.Session()

    session.get(
        "https://www.aastocks.com/tc/cnhk/quote/quick-quote.aspx",
        headers=headers,
        timeout=15,
    )
    time.sleep(random.uniform(0.8, 2.0))

    resp = session.get(URL, headers=headers, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    price_tag = soup.find(id="SQ_Last")
    change_tag = soup.find(id="SQ_Change")

    if not price_tag or not change_tag:
        raise RuntimeError("页面元素未找到，可能被反爬或结构变更")

    price = float(price_tag.get_text(strip=True))
    change_text = change_tag.get_text(strip=True)
    change_val, change_pct = parse_change(change_text)

    result = {
        "symbol": SYMBOL,
        "price": price,
        "change": change_val,
        "change_pct": change_pct,
        "raw_change": change_text,
    }

    return result


if __name__ == "__main__":
    data = fetch_price()
    print(f"代码    : {data['symbol']}")
    print(f"前复权价 : {data['price']}")
    print(f"涨跌额  : {data['change']}")
    print(f"涨跌幅  : {data['change_pct']}%")
