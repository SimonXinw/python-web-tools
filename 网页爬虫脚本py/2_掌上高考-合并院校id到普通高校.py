import os

import pandas as pd


ID_COLUMN = "id"
CAMPUS_KEYWORD = "校区"


def normalize_name(name):
    if pd.isna(name):
        return ""

    return str(name).replace(" ", "").replace("　", "").strip()


def build_empty_row(columns, next_index, school_name, school_id):
    row = {col: pd.NA for col in columns if col != "_match_name"}
    row["序号"] = next_index
    row["学校名称"] = school_name
    row[ID_COLUMN] = school_id
    return row


def append_school_row(school_df, school_name, school_id):
    next_index = int(school_df["序号"].max()) + 1 if len(school_df) else 1
    new_row = build_empty_row(school_df.columns, next_index, school_name, school_id)
    school_df = pd.concat([school_df, pd.DataFrame([new_row])], ignore_index=True)
    school_df.loc[school_df.index[-1], "_match_name"] = normalize_name(school_name)
    return school_df


def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(current_dir, "高考教育院校id_map_表.csv")
    xls_path = os.path.join(current_dir, "普通高校.xls")
    output_xlsx_path = os.path.join(current_dir, "普通高校_带id.xlsx")

    gaokao_df = pd.read_csv(csv_path, encoding="utf-8-sig")
    school_df = pd.read_excel(xls_path)

    if ID_COLUMN not in school_df.columns:
        school_df[ID_COLUMN] = pd.NA

    gaokao_df = gaokao_df[gaokao_df["状态"] == "成功"].copy()
    gaokao_df["院校名称"] = gaokao_df["院校名称"].fillna("").astype(str).str.strip()
    gaokao_df = gaokao_df[gaokao_df["院校名称"] != ""]

    school_df["_match_name"] = school_df["学校名称"].map(normalize_name)

    campus_added = 0
    matched_updated = 0
    unmatched_added = 0

    for _, item in gaokao_df.iterrows():
        school_name = item["院校名称"]
        school_id = str(item["代码"]).strip()
        normalized_name = normalize_name(school_name)

        if CAMPUS_KEYWORD in school_name:
            school_df = append_school_row(school_df, school_name, school_id)
            campus_added += 1
            continue

        matched_rows = school_df[school_df["_match_name"] == normalized_name]

        if len(matched_rows) > 0:
            row_index = matched_rows.index[0]
            school_df.at[row_index, ID_COLUMN] = school_id
            matched_updated += 1
            continue

        school_df = append_school_row(school_df, school_name, school_id)
        unmatched_added += 1

    school_df = school_df.drop(columns=["_match_name"])
    school_df.to_excel(output_xlsx_path, index=False)

    print("合并完成")
    print(f"- 输入 CSV（仅成功）: {len(gaokao_df)} 条")
    print(f"- 校区新增行: {campus_added} 条")
    print(f"- 名称匹配并写入 id: {matched_updated} 条")
    print(f"- 未匹配新增行: {unmatched_added} 条")
    print(f"- 输出文件: {output_xlsx_path}（原 普通高校.xls 未修改）")


if __name__ == "__main__":
    main()
