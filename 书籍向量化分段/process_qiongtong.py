"""
穷通宝鉴 JSONL → Markdown 转换脚本
读取已生成的 JSONL，输出 Dify 友好的 Markdown 文件
分段标识符：# ；最大长度建议 4000
"""

import sys
import re
import json
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

# ── 路径配置 ─────────────────────────────────────────────────────────────────
BASE_DIR  = Path(r"C:\Users\Administrator\Desktop\projects\xw\python-web-tools") / "书籍向量化分段"
OUT_DIR   = BASE_DIR / "output"
IN_JSONL = OUT_DIR / "[穷通宝鉴+造化元钥]原文.jsonl"
OUT_MD   = OUT_DIR / "[穷通宝鉴+造化元钥]原文.md"

META_KEYS    = ["day_master", "month_label", "month_branch", "section_type", "core_element"]
META_LABELS  = {
    "day_master"  : "日主",
    "month_label" : "月份",
    "month_branch": "月令",
    "section_type": "类型",
    "core_element": "用神",
}


def clean_value(value: str) -> str:
    """清理字符串：去控制字符、统一换行、去行首尾空白、压缩空行、空值填无"""
    if not isinstance(value, str):
        return "无" if value is None else str(value)
    value = value.replace("\u000b", "\n")
    value = re.sub(r"\r\n|\r", "\n", value)
    lines = [line.strip() for line in value.split("\n")]
    lines = [line for line in lines if line]
    value = "\n".join(lines).strip()
    return value if value else "无"


def build_heading(rec: dict) -> str:
    """生成 Markdown 一级标题，用于 Dify 分段标识"""
    day    = rec.get("day_master", "无")
    label  = rec.get("month_label", "")
    branch = rec.get("month_branch", "")
    stype  = rec.get("section_type", "")

    label_val  = "" if label  in ("", "无") else label
    branch_val = "" if branch in ("", "无") else branch

    if label_val and branch_val:
        month_part = f"生于{label_val}（{branch_val}）"
    elif branch_val:
        month_part = f"生于{branch_val}"
    elif label_val:
        month_part = f"生于{label_val}"
    else:
        month_part = ""

    return f"# {day}{month_part} · {stype}" if month_part else f"# {day} · {stype}"


def build_md_block(rec: dict) -> str:
    """把一条记录渲染成 Markdown 段落"""
    heading = build_heading(rec)

    meta_lines = "\n".join(
        f"{META_LABELS.get(k, k)}: {rec.get(k, '无')}"
        for k in META_KEYS
    )

    content = rec.get("content", "无").strip()

    return f"{heading}\n\n---\n{meta_lines}\n---\n\n{content}"


def main():
    if not IN_JSONL.exists():
        print(f"[错误] 找不到 JSONL 文件：{IN_JSONL}")
        return

    records = []
    with IN_JSONL.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                raw = json.loads(line)
                cleaned = {k: clean_value(v) for k, v in raw.items()}
                records.append(cleaned)

    print(f"读取 JSONL：{len(records)} 条记录")

    # ── 构建 MD 块并统计 chunk 大小 ─────────────────────────────────────────
    blocks = [build_md_block(rec) for rec in records]

    chunk_sizes = sorted(
        [(len(b), b, records[i]) for i, b in enumerate(blocks)],
        key=lambda x: x[0],
        reverse=True,
    )

    max_size, max_block, max_rec = chunk_sizes[0]
    min_size = chunk_sizes[-1][0]
    avg_size = sum(s for s, _, _ in chunk_sizes) // len(chunk_sizes)

    print("\n─── Chunk 字符数统计（MD 口径）───")
    print(f"  记录总数  : {len(chunk_sizes)}")
    print(f"  最大 chunk: {max_size} 字符")
    print(f"  最小 chunk: {min_size} 字符")
    print(f"  平均 chunk: {avg_size} 字符")
    print(f"\n  [最大 chunk 详情]")
    print(f"  day_master  = {max_rec['day_master']}")
    print(f"  month       = {max_rec.get('month_label', '')}（{max_rec.get('month_branch', '')}）")
    print(f"  section_type= {max_rec['section_type']}")
    print(f"  chunk 内容预览（前 200 字）:\n  {max_block[:200]}...")
    print(f"\n  TOP 5 最大 chunk:")
    for rank, (size, _, rec) in enumerate(chunk_sizes[:5], 1):
        month_label  = rec.get("month_label", "")
        month_branch = rec.get("month_branch", "")
        month_str = f"{month_label}({month_branch})" if month_label else (month_branch or "总论")
        print(f"  [{rank}] {size} 字符  |  {rec['day_master']} × {month_str}  {rec['section_type']}")

    # ── 写入 Markdown 文件 ────────────────────────────────────────────────────
    md_content = "\n\n".join(blocks) + "\n"
    OUT_MD.write_text(md_content, encoding="utf-8")
    print(f"\n已保存 Markdown → {OUT_MD}  ({len(records)} 条记录，{len(md_content)} 字符)")

    print("\n─── 前 3 条预览 ───")
    for i, rec in enumerate(records[:3]):
        print(f"\n[{i+1}] {build_heading(rec)}")
        print(f"     core_element: {rec['core_element']}")
        print(f"     content 前 80 字: {rec['content'][:80]}...")


if __name__ == "__main__":
    main()
