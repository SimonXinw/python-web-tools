import os

import pandas as pd


SCHOOL_NAME_COLUMN = "学校名称"
QUERY_NAME_COLUMN = "查询院校名称"
# 普通高校列名 -> 结果表列名（备注写入院校备注，不覆盖夸克爬取的备注列）
SOURCE_TO_RESULT_COLUMN_MAP = {
    "主管部门": "主管部门",
    "所在地": "所在地",
    "办学层次": "办学层次",
    "备注": "院校备注",
}


def normalize_name(name):
    if pd.isna(name):
        return ""

    return str(name).strip()


def build_source_lookup(source_df):
    lookup = {}

    for _, row in source_df.iterrows():
        key = normalize_name(row[SCHOOL_NAME_COLUMN])
        if not key or key in lookup:
            continue

        lookup[key] = {
            result_col: row[source_col]
            for source_col, result_col in SOURCE_TO_RESULT_COLUMN_MAP.items()
            if source_col in source_df.columns
        }

    return lookup


def fill_result_info(source_path, result_path):
    source_df = pd.read_excel(source_path)
    result_df = pd.read_excel(result_path)

    if SCHOOL_NAME_COLUMN not in source_df.columns:
        raise ValueError(f"源表缺少列: {SCHOOL_NAME_COLUMN}")

    if QUERY_NAME_COLUMN not in result_df.columns:
        raise ValueError(f"结果表缺少列: {QUERY_NAME_COLUMN}")

    lookup = build_source_lookup(source_df)

    for result_col in SOURCE_TO_RESULT_COLUMN_MAP.values():
        if result_col not in result_df.columns:
            result_df[result_col] = pd.NA
        result_df[result_col] = result_df[result_col].astype("object")

    matched_rows = 0
    unmatched_names = set()

    for index, row in result_df.iterrows():
        query_name = normalize_name(row[QUERY_NAME_COLUMN])
        if not query_name:
            continue

        source_info = lookup.get(query_name)
        if source_info is None:
            unmatched_names.add(query_name)
            continue

        matched_rows += 1
        for result_col, value in source_info.items():
            result_df.at[index, result_col] = value

    result_df.to_excel(result_path, index=False)

    print("院校信息完善完成")
    print(f"- 源表: {source_path}")
    print(f"- 结果表: {result_path}")
    print(f"- 源表可匹配学校: {len(lookup)} 所")
    print(f"- 结果表匹配并更新行: {matched_rows} 行")
    print(f"- 未匹配院校名称: {len(unmatched_names)} 个")
    if unmatched_names:
        print("- 未匹配列表:", "、".join(sorted(unmatched_names)))


def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    source_path = os.path.join(current_dir, "普通高校.xlsx")
    result_path = os.path.join(current_dir, "夸克-江西-院校专业表.xlsx")

    fill_result_info(source_path, result_path)


if __name__ == "__main__":
    main()
